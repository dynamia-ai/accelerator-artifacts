"""Publish an approved, signed staged image to GHCR and emit a public release record."""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from github import GitHub
from metadata import (
    BUILD_FILES,
    REPOSITORY,
    ROOT,
    SHA,
    TAG,
    Error,
    Lock,
    build_platform,
    load_local,
    lock_path,
)

WORKFLOW = f"{REPOSITORY}/.github/workflows/release.yml"
RELEASE_CONTROLS = (
    ".github/workflows/release.yml",
    ".github/workflows/release-image.yml",
    ".python-version",
    "scripts/github.py",
    "scripts/metadata.py",
    "scripts/release.py",
    "scripts/record_release.py",
)
RECIPE_FILES = ("upstream.yaml", "LICENSING.md", "README.md", *BUILD_FILES)
DIGEST = re.compile(r"sha256:[a-f0-9]{64}")
IMAGE_REPO = re.compile(r"[a-z0-9][a-z0-9.-]*\.[a-z]+(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)+")


def required(env, key):
    if not env.get(key):
        raise Error(f"missing protected release setting: {key}")
    return env[key]


def require_context(env):
    for name, value in {
        "GITHUB_ACTIONS": "true",
        "GITHUB_REPOSITORY": REPOSITORY,
        "PUBLIC_RELEASE_ENABLED": "true",
    }.items():
        if env.get(name) != value:
            raise Error(
                "publication requires the enabled protected workflow in the original repository"
            )
    event = env.get("GITHUB_EVENT_NAME")
    tag = required(env, "RELEASE_REF").removeprefix("refs/tags/")
    refs = {"push": f"refs/tags/{tag}", "workflow_dispatch": "refs/heads/main"}
    ref = refs.get(event)
    if (
        not ref
        or env.get("GITHUB_REF") != ref
        or env.get("GITHUB_WORKFLOW_REF") != f"{WORKFLOW}@{ref}"
    ):
        raise Error("publication requires a release tag push or a retry from main")
    if not SHA.fullmatch(env.get("GITHUB_SHA", "")):
        raise Error("publication requires a valid workflow commit")
    return tag


def parse_project_tag(tag):
    parts = tag.split("/")
    if len(parts) != 4 or parts[0] != "release" or not TAG.fullmatch(parts[3]):
        raise Error(
            "release ref must name a project release tag: release/<vendor>/<component>/vX.Y.Z"
        )
    component = "/".join(parts[1:3])
    lock_path(component)
    return component, parts[3]


@dataclass(frozen=True)
class ReleaseTarget:
    component: str
    tag: str
    lock: Lock
    platform: str
    licensing_sha: str
    recipe_commit: str

    @property
    def image(self):
        return f"ghcr.io/{REPOSITORY}/{self.component}"

    @property
    def environment(self):
        return "public-ghcr-" + self.component.replace("/", "--")


def licensing_digest(root, component, tag):
    path = root / lock_path(component)
    license_file = path.with_name("LICENSING.md")
    if license_file.is_symlink() or not license_file.is_file():
        raise Error("approved version-specific LICENSING.md is required")
    data = license_file.read_bytes()
    lines = data.decode().splitlines()
    versions = [line for line in lines if line.startswith("Upstream-Tag:")]
    status = [line for line in lines if line.startswith("Public-Redistribution:")]
    if versions != [f"Upstream-Tag: {tag}"] or status != ["Public-Redistribution: approved"]:
        raise Error("public redistribution is not approved for this upstream version")
    return hashlib.sha256(data).hexdigest()


def quiet(args, operation, *, data=None, env=None, timeout=120):
    result = subprocess.run(
        args, input=data, capture_output=True, env=env, timeout=timeout, check=False
    )
    if result.returncode:
        raise Error(f"{operation} failed")
    return result.stdout


def verify_evidence(env, scratch, target):
    evidence = required(env, "STAGING_EVIDENCE").encode()
    payload = scratch / "evidence.json"
    signature = scratch / "evidence.sig"
    pubkey = scratch / "builder.pem"
    payload.write_bytes(evidence)
    signature.write_bytes(base64.b64decode(required(env, "STAGING_SIGNATURE"), validate=True))
    pubkey.write_text(required(env, "STAGING_BUILDER_PUBLIC_KEY"), encoding="utf-8")
    quiet(
        [
            "openssl",
            "dgst",
            "-sha256",
            "-verify",
            str(pubkey),
            "-signature",
            str(signature),
            str(payload),
        ],
        "verify staging evidence signature",
    )

    proof = json.loads(evidence)
    expected = {
        "component": target.component,
        "upstream_repository": target.lock.repository,
        "upstream_tag": target.lock.tag,
        "upstream_commit": target.lock.commit,
        "recipe_commit": target.recipe_commit,
        "licensing_sha256": target.licensing_sha,
        "builder": required(env, "STAGING_BUILDER"),
        "platform": target.platform,
        "source_repository": required(env, "STAGING_IMAGE_REPOSITORY"),
    }
    if set(proof) != expected.keys() | {"digest"} or any(
        proof.get(key) != value for key, value in expected.items()
    ):
        raise Error(
            "staging evidence does not match the reviewed recipe, licensing, builder or source"
        )
    if not IMAGE_REPO.fullmatch(expected["source_repository"]) or not DIGEST.fullmatch(
        proof["digest"]
    ):
        raise Error("staging evidence requires a valid digest-pinned image reference")
    return proof


def ghcr_auth(env, scratch):
    actor = required(env, "GITHUB_ACTOR")
    token = required(env, "GH_TOKEN")
    auth = base64.b64encode(f"{actor}:{token}".encode()).decode()
    file = scratch / "ghcr-auth.json"
    file.write_text(json.dumps({"auths": {"ghcr.io": {"auth": auth}}}), encoding="utf-8")
    return file


def raw_manifest(reference, auth, *, missing_ok=False, env=None):
    result = subprocess.run(
        ["skopeo", "inspect", "--authfile", str(auth), "--raw", f"docker://{reference}"],
        capture_output=True,
        timeout=120,
        env=env,
        check=False,
    )
    if result.returncode:
        if missing_ok and re.search(
            rb"\b(?:manifest|name)[ _]unknown\b", result.stderr, re.IGNORECASE
        ):
            return None
        raise Error("image manifest inspection failed")
    return result.stdout


def manifest_digest(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def platform_digests(repository, raw, auth, platform, env=None):
    # A single-platform recipe may still be stored as a single-entry manifest index.
    expected = tuple(platform.split("/"))
    digest = manifest_digest(raw)
    data = json.loads(raw)
    if "manifests" in data:
        entries = data["manifests"]
        if (
            len(entries) != 1
            or (
                entries[0]["platform"]["os"],
                entries[0]["platform"]["architecture"],
            )
            != expected
        ):
            raise Error(f"image index does not contain exactly one {platform} image")
        digest = entries[0]["digest"]
        if not DIGEST.fullmatch(digest):
            raise Error("invalid platform manifest digest")
        raw = raw_manifest(f"{repository}@{digest}", auth, env=env)
        if manifest_digest(raw) != digest or "manifests" in json.loads(raw):
            raise Error("platform manifest does not match its descriptor")
    config = json.loads(
        quiet(
            [
                "skopeo",
                "inspect",
                "--config",
                "--authfile",
                str(auth),
                f"docker://{repository}@{digest}",
            ],
            "inspect image config",
            env=env,
        )
    )
    if (config["os"], config["architecture"]) != expected:
        raise Error("image config does not match the recipe platform")
    return [{"platform": platform, "manifest_digest": digest}]


def transfer(
    source, destination, tag, digest, source_auth, destination_auth, scratch, pre_write, *, platform
):
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(scratch),
        "XDG_RUNTIME_DIR": str(scratch),
        "XDG_CONFIG_HOME": str(scratch),
        "DOCKER_CONFIG": str(scratch),
    }
    raw = raw_manifest(f"{source}@{digest}", source_auth, env=env)
    if manifest_digest(raw) != digest:
        raise Error("staging digest does not match signed evidence")
    platforms = platform_digests(source, raw, source_auth, platform, env=env)
    target = f"{destination}:{tag}"
    existing = raw_manifest(target, destination_auth, missing_ok=True, env=env)
    if existing is not None and manifest_digest(existing) != digest:
        raise Error("public tag already points to a different digest")
    if existing is None:
        pre_write()
        quiet(
            [
                "skopeo",
                "copy",
                "--all",
                "--preserve-digests",
                "--src-authfile",
                str(source_auth),
                "--dest-authfile",
                str(destination_auth),
                f"docker://{source}@{digest}",
                f"docker://{target}",
            ],
            "copy verified artifact to GHCR",
            timeout=1200,
            env=env,
        )

    anonymous = scratch / "anonymous.json"
    anonymous.write_text('{"auths":{}}\n', encoding="utf-8")
    try:
        public_tag = raw_manifest(target, anonymous, env=env)
    except Error as error:
        raise Error(
            "GHCR tag is not anonymously readable; verify package visibility and retry"
        ) from error
    if manifest_digest(public_tag) != digest:
        raise Error("public tag does not match the expected digest")
    destination_raw = raw_manifest(f"{destination}@{digest}", anonymous, env=env)
    if manifest_digest(destination_raw) != digest:
        raise Error("public image manifest does not match its digest")
    if platform_digests(destination, destination_raw, anonymous, platform, env=env) != platforms:
        raise Error("public image platforms or manifest digests do not match staging")
    # The registry digest is already verified. An OCI scratch layout may convert Docker media types.
    quiet(
        [
            "skopeo",
            "copy",
            "--all",
            "--src-authfile",
            str(anonymous),
            f"docker://{destination}@{digest}",
            f"oci:{scratch / 'anonymous-pull'}:verified",
        ],
        "pull public image anonymously",
        timeout=1200,
        env=env,
    )
    return platforms


def preflight(env, root=ROOT):
    tag = require_context(env)
    component, upstream_tag = parse_project_tag(tag)
    lock = load_local(root, component)
    if upstream_tag != lock.tag:
        raise Error("release ref must name a project release tag for the upstream lock")
    platform = build_platform(root, component)
    if not platform:
        raise Error("component has no publication recipe")
    license_sha = licensing_digest(root, component, lock.tag)
    directory = (root / lock_path(component)).parent
    for name in RECIPE_FILES:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise Error(f"release recipe requires a regular {name} file")

    api = GitHub(required(env, "GH_TOKEN"))
    recipe_commit = api.tag_commit(REPOSITORY, tag)
    workflow_commit = env["GITHUB_SHA"]
    if recipe_commit is None:
        raise Error("project release tag must already exist")
    if env["GITHUB_EVENT_NAME"] == "push" and recipe_commit != workflow_commit:
        raise Error("project release tag no longer points to the triggering commit")

    main = api.main()
    if not api.is_ancestor(recipe_commit, main):
        raise Error("project release tag must point to a reviewed commit on main")

    recipe_paths = tuple(
        (Path(lock_path(component)).parent / name).as_posix() for name in RECIPE_FILES
    )
    if main != workflow_commit:
        for path in (*RELEASE_CONTROLS, *recipe_paths):
            if api.file_at(path, main).encode() != (root / path).read_bytes():
                raise Error("publication controls or the reviewed recipe have changed on main")
    if recipe_commit != workflow_commit:
        for path in recipe_paths:
            if api.file_at(path, recipe_commit).encode() != (root / path).read_bytes():
                raise Error("tagged recipe or licensing differs from current main")
    return ReleaseTarget(component, tag, lock, platform, license_sha, recipe_commit)


def run(env, output, root=ROOT):
    target = preflight(env, root)
    lock = target.lock
    destination = target.image
    if env.get("RELEASE_ENVIRONMENT") != target.environment:
        raise Error("publication requires the component release environment")

    def require_current_release():
        if preflight(env, root) != target:
            raise Error("approved release changed before publication")

    with tempfile.TemporaryDirectory(prefix="ghcr-release-") as temp:
        scratch = Path(temp)
        proof = verify_evidence(env, scratch, target)
        if proof["source_repository"] == destination:
            raise Error("staging and public repositories must be distinct")
        source_auth = scratch / "staging-auth.json"
        staging_auth = json.loads(required(env, "STAGING_AUTH"))
        if set(staging_auth.get("auths", {})) != {proof["source_repository"].split("/")[0]}:
            raise Error("staging auth must contain only the approved private registry")
        source_auth.write_text(json.dumps(staging_auth), encoding="utf-8")
        destination_auth = ghcr_auth(env, scratch)
        platforms = transfer(
            proof["source_repository"],
            destination,
            lock.tag,
            proof["digest"],
            source_auth,
            destination_auth,
            scratch,
            require_current_release,
            platform=target.platform,
        )

    source_path = Path(lock_path(target.component)).parent.as_posix()
    record = {
        "component": target.component,
        "upstream_repository": lock.repository,
        "upstream_tag": lock.tag,
        "upstream_commit": lock.commit,
        "recipe_commit": target.recipe_commit,
        "image": f"{destination}:{lock.tag}",
        "digest": proof["digest"],
        "platforms": platforms,
        "verified_at": datetime.now(UTC).isoformat(),
        "licensing": f"https://github.com/{REPOSITORY}/blob/{target.recipe_commit}/{source_path}/LICENSING.md",
        "installation": f"https://github.com/{REPOSITORY}/blob/{target.recipe_commit}/{source_path}/README.md",
    }
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("Public image and anonymous pull verified. Release record saved.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--github-output", type=Path, help="write routing outputs with --check")
    args = parser.parse_args()
    if args.github_output and not args.check:
        parser.error("--github-output requires --check")
    os.umask(0o077)
    try:
        if args.check:
            target = preflight(os.environ)
            if args.github_output:
                with args.github_output.open("a", encoding="utf-8") as output:
                    print(f"component={target.component}", file=output)
                    print(f"release-ref=refs/tags/{target.tag}", file=output)
                    print(f"environment={target.environment}", file=output)
            print("Project release tag and component licensing are eligible for protected review.")
        else:
            run(os.environ, args.output)
    except (Error, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        # Lower-level errors can contain private URLs, registry responses or temporary credentials.
        sys.exit(
            str(error)
            if isinstance(error, Error)
            else "release validation or service operation failed"
        )


if __name__ == "__main__":
    main()
