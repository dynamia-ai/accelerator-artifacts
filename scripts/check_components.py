"""Discover component checks and validate source locks without write permissions."""

import argparse
import json
import os
import subprocess
import sys

from github import GitHub
from metadata import (
    ROOT,
    SHA,
    Error,
    build_platform,
    components,
    load_local,
    lock_path,
    read_base_lock,
)


def inventory(root):
    items = list(components(root))
    if not items:
        raise Error("no components found in vendors")
    for item in items:
        lock_path(item)
    return items


def verify_tag(api, lock):
    actual = api.tag_commit(lock.slug, lock.tag)
    if actual != lock.commit:
        raise Error(
            f"{lock.slug} {lock.tag} locked at {lock.commit}; upstream is {actual or 'missing'}"
        )


def check(root, component, base, api):
    current = load_local(root, component)
    build_platform(root, component)
    previous = read_base_lock(root, component, base) if base else None
    if previous and current != previous:
        if (
            current.slug.casefold() == previous.slug.casefold()
            and current.version <= previous.version
        ):
            raise Error("changed lock for the same upstream must advance the version")
        if api:
            verify_tag(api, previous)

    if api:
        verify_tag(api, current)
        release = api.release(current.slug, current.tag)
        if (
            not release
            or release["tag_name"] != current.tag
            or release["draft"] is not False
            or release["prerelease"] is not False
        ):
            raise Error(f"{current.slug} {current.tag} is not a published stable GitHub Release")
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--matrix", action="store_true")
    mode.add_argument("--component")
    parser.add_argument("--base", help="full PR base commit SHA")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.base and not SHA.fullmatch(args.base):
        parser.error("--base must be a full SHA")

    try:
        items = [args.component] if args.component else inventory(ROOT)
        if args.matrix:
            print(
                json.dumps(
                    {"include": [{"component": item} for item in items]}, separators=(",", ":")
                )
            )
            return 0
    except (Error, OSError) as error:
        print(error, file=sys.stderr)
        return 1

    failed = False
    api = None if args.offline else GitHub(os.environ.get("GH_TOKEN"))
    for component in items:
        try:
            lock = check(ROOT, component, args.base, api)
            print(f"{component}: lock valid ({lock.tag})")
        except (
            Error,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            subprocess.SubprocessError,
        ) as error:
            detail = (
                str(error) if isinstance(error, Error) else "validation or GitHub operation failed"
            )
            print(f"{component}: {detail}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
