"""Attach a verified public publication record, resuming an interrupted draft."""

import json
import os
import subprocess
import sys
from pathlib import Path

from github import GitHub, run_gh
from metadata import REPOSITORY, Error
from release import DIGEST, GHCR_IMAGE, preflight, project_tag, required


def attach(env, component, path):
    lock, license_sha, recipe = preflight(env, component)
    token = required(env, "GH_TOKEN")
    api = GitHub(token)
    record = json.loads(path.read_bytes())
    asset_name = "release-record.json"
    if (
        path.name != asset_name
        or record["component"] != component
        or record["upstream_repository"] != lock.repository
        or record["upstream_tag"] != lock.tag
        or record["upstream_commit"] != lock.commit
        or record["recipe_commit"] != recipe
        or record["image"] != f"{GHCR_IMAGE}:{lock.tag}"
        or not DIGEST.fullmatch(record["digest"])
    ):
        raise Error("release record does not match the current workflow and reviewed lock")

    tag = project_tag(component, lock.tag)
    notes = (
        f"Publication record for {component} {lock.tag} at recipe commit {record['recipe_commit']}."
    )
    repo = ["--repo", REPOSITORY]

    def find():
        pages = api.api(
            f"repos/{REPOSITORY}/releases?per_page=100",
            pages=True,
            operation="list publication releases",
        )
        return next((entry for page in pages for entry in page if entry["tag_name"] == tag), None)

    release = find()

    def require_current_release():
        if preflight(env, component) != (lock, license_sha, recipe):
            raise Error("approved release changed before recording")

    if release is None:
        require_current_release()
        try:
            run_gh(
                token,
                [
                    "release",
                    "create",
                    tag,
                    *repo,
                    "--draft",
                    "--verify-tag",
                    "--title",
                    tag,
                    "--notes",
                    notes,
                ],
                "create release draft",
            )
        except Error, subprocess.TimeoutExpired:
            if find() is None:
                raise
        release = find()
        if release is None:
            raise Error("publication draft could not be confirmed")

    def record_asset(entry):
        return next((asset for asset in entry["assets"] if asset["name"] == asset_name), None)

    asset = record_asset(release)
    if (
        asset is not None
        and asset.get("state") == "starter"
        and asset.get("size") == 0
        and release["draft"]
    ):
        # A documented upstream upload failure can leave an empty placeholder with its own asset ID.
        require_current_release()
        route = f"repos/{REPOSITORY}/releases/assets/{asset['id']}"
        run_gh(token, ["api", "--method", "DELETE", route], "remove failed draft asset placeholder")
        asset = None
    if asset is None:
        if not release["draft"]:
            raise Error("published release is missing the expected record")
        require_current_release()
        run_gh(token, ["release", "upload", tag, str(path), *repo], "attach public release record")
        refreshed = find()
        if refreshed is None or refreshed["id"] != release["id"]:
            raise Error("release draft changed during attachment upload")
        release = refreshed
        asset = record_asset(release)
        if asset is None:
            raise Error("uploaded public Release attachment could not be confirmed")

    route = f"repos/{REPOSITORY}/releases/assets/{asset['id']}"
    existing = json.loads(
        run_gh(
            token,
            [
                "api",
                route,
                "-H",
                "Accept: application/octet-stream",
            ],
            "verify existing release attachment",
        )
    )
    if {key: value for key, value in existing.items() if key != "verified_at"} != {
        key: value for key, value in record.items() if key != "verified_at"
    }:
        raise Error("existing release attachment describes a different image")

    tag_sha = api.tag_commit(REPOSITORY, tag)
    if tag_sha != recipe:
        raise Error("release tag changed before publication")
    if release["draft"]:
        require_current_release()
        run_gh(
            token,
            ["release", "edit", tag, *repo, "--draft=false", "--latest=false"],
            "publish GitHub Release",
        )
    if api.tag_commit(REPOSITORY, tag) != recipe:
        raise Error("published GitHub Release tag could not be verified")
    print("Verified public GitHub Release attachment.")


if __name__ == "__main__":
    try:
        attach(os.environ, sys.argv[1], Path(sys.argv[2]))
    except (
        Error,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        subprocess.SubprocessError,
    ) as error:
        sys.exit(
            str(error)
            if isinstance(error, Error)
            else "release record validation or GitHub operation failed"
        )
