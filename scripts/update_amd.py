"""Prepare an AMD Exporter upgrade and verify new image pins in pull requests."""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import replace
from pathlib import Path

from scripts import components

COMPONENT = "amd/device-metrics-exporter"
DIRECTORY = Path("vendors") / COMPONENT
UPSTREAM = "ROCm/device-metrics-exporter"
VERSION = r"v(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2}"


def make_value(makefile: str, name: str) -> str:
    values = re.findall(rf"^{name} := (.+)$", makefile, re.MULTILINE)
    if len(values) != 1:
        raise ValueError(f"Expected one {name} assignment in the AMD Makefile")
    return values[0]


def image_digest(image: str, version: str) -> str:
    source = f"docker://{image}:{version}"
    metadata = components.run(
        "skopeo",
        "--override-os",
        "linux",
        "--override-arch",
        "amd64",
        "inspect",
        "--no-tags",
        "--format",
        "{{.Digest}} {{.Os}}/{{.Architecture}}",
        source,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64} linux/amd64", metadata):
        raise ValueError(f"{source}: expected a linux/amd64 manifest digest, got {metadata!r}")
    return metadata.split()[0]


def image_pin(manifest: str, makefile: str) -> tuple[str, str, str]:
    return (
        make_value(makefile, "APP_IMAGE"),
        tomllib.loads(manifest)["version"],
        make_value(makefile, "APP_DIGEST"),
    )


def check_pin(base: str) -> None:
    directory = components.ROOT / DIRECTORY
    manifest = directory / "component.toml"
    makefile = directory / "Makefile"
    image, version, pinned = image_pin(manifest.read_text(), makefile.read_text())
    previous = [
        components.run(
            "git",
            "show",
            f"{base}:{path.relative_to(components.ROOT).as_posix()}",
            cwd=components.ROOT,
            capture_output=True,
            text=True,
        ).stdout
        for path in (manifest, makefile)
    ]
    if (image, version, pinned) == image_pin(*previous):
        return
    actual = image_digest(image, version)
    if pinned != actual:
        raise ValueError(f"{image}:{version} resolves to {actual}, but APP_DIGEST is {pinned}")


def update(requested_version: str | None) -> None:
    selected = components.component(COMPONENT)
    if requested_version is not None and not re.fullmatch(VERSION, requested_version):
        raise ValueError(f"Expected a release version such as v1.5.4, got {requested_version!r}")
    release = json.loads(
        components.run(
            "gh",
            "release",
            "view",
            *([requested_version] if requested_version else []),
            "--repo",
            UPSTREAM,
            "--json",
            "tagName,isDraft,isPrerelease,url",
            capture_output=True,
        ).stdout
    )
    version = release["tagName"]
    if release["isDraft"] or release["isPrerelease"] or not re.fullmatch(VERSION, version):
        raise ValueError(f"Expected a stable {UPSTREAM} release, got {version!r}")
    if version == selected.version and requested_version is None:
        print(f"{COMPONENT} is already at {version}")
        return
    if tuple(map(int, version[1:].split("."))) < tuple(map(int, selected.version[1:].split("."))):
        raise ValueError(f"{COMPONENT} is at {selected.version}, newer than {version}")

    makefile = (selected.directory / "Makefile").read_text()
    image = make_value(makefile, "APP_IMAGE")
    chart = make_value(makefile, "CHART")
    chart_url = (
        make_value(makefile, "CHART_URL").replace("$(CHART)", chart).replace("$(VERSION)", version)
    )
    pinned = image_digest(image, version)
    with tempfile.TemporaryDirectory(prefix="accelerator-amd-update-") as temporary:
        scratch = Path(temporary)
        components.run("helm", "pull", chart_url, "--destination", temporary)
        chart_sha256 = components.digest(
            (scratch / f"{chart}-{version}.tgz").read_bytes()
        ).removeprefix("sha256:")
        license_text = components.run(
            "gh",
            "api",
            "-H",
            "Accept: application/vnd.github.raw+json",
            f"repos/{UPSTREAM}/contents/LICENSE?ref={version}",
            capture_output=True,
        ).stdout

        directory = scratch / DIRECTORY
        directory.mkdir(parents=True)
        shutil.copyfile(selected.directory / "README.md", directory / "README.md")
        (scratch / "scripts").mkdir()
        shutil.copyfile(components.ROOT / "scripts/component.mk", scratch / "scripts/component.mk")
        manifest = (selected.directory / "component.toml").read_text()
        manifest, changed = re.subn(
            r"^version\s*=.*$", f'version = "{version}"', manifest, count=1, flags=re.MULTILINE
        )
        if changed != 1:
            raise ValueError("Expected a version assignment in the AMD manifest")
        for name, value in (
            ("APP_VERSION", version),
            ("APP_DIGEST", pinned),
            ("CHART_SHA256", chart_sha256),
        ):
            makefile = makefile.replace(
                f"{name} := {make_value(makefile, name)}\n", f"{name} := {value}\n"
            )
        (directory / "component.toml").write_text(manifest)
        (directory / "Makefile").write_text(makefile)
        (directory / "LICENSE").write_bytes(license_text)
        components.build(
            replace(selected, directory=directory, version=version), scratch / "artifacts"
        )

        for name in ("component.toml", "Makefile", "LICENSE"):
            shutil.copyfile(directory / name, selected.directory / name)

    print(f"Release: {release['url']}")
    print(f"Image: {image}:{version} ({pinned}, linux/amd64)")
    print(f"Chart: {chart_url} (SHA-256: {chart_sha256})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Validate and apply an upgrade in the worktree")
    prepare.add_argument(
        "--version", help="Use this ROCm release instead of the latest stable release"
    )
    check = commands.add_parser(
        "check-pin", help="Verify a changed image pin against its upstream tag"
    )
    check.add_argument("--base", required=True, help="Base Git revision to compare against")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            update(args.version)
        else:
            check_pin(args.base)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            stderr = (
                error.stderr.decode(errors="replace")
                if isinstance(error.stderr, bytes)
                else error.stderr
            )
            print(stderr.rstrip(), file=sys.stderr)
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
