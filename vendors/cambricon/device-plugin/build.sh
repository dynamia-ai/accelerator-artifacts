#!/usr/bin/env bash
set -euo pipefail
umask 077

recipe="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
root="$(cd "$recipe/../../.." && pwd -P)"
mode="${1:---build}"
if [[ "$#" -gt 1 || ( "$mode" != --build && "$mode" != --check-inputs ) ]]; then
    echo 'Usage: build.sh [--check-inputs|--build]' >&2
    exit 2
fi

if [[ "$mode" == --build && ( "${CAMBRICON_AUTHORIZED_BUILD:-}" != 1 || "${GITHUB_ACTIONS:-}" == true ) ]]; then
    echo 'Build requires an authorized environment and CAMBRICON_AUTHORIZED_BUILD=1.' >&2
    exit 1
fi

# Keep SDK inputs external, even when a supplied path is a symlink.
lock="$(PYTHONPATH="$root/scripts" python3 - "$recipe" "$root" <<'PY'
import os
from pathlib import Path
import stat
import sys

from metadata import Error, parse_lock

recipe, root = map(Path, sys.argv[1:])
try:
    lock = parse_lock((recipe / "upstream.yaml").read_text())
except (Error, OSError) as error:
    sys.exit(f"Invalid Cambricon lock: {error}")

bad = False
for var, name in [
    ("CAMBRICON_CNDEV_HEADER", "cndev.h (6.5.24)"),
    ("CAMBRICON_LIBCNDEV", "libcndev.so"),
    ("CAMBRICON_LIBCNTOPO", "libcntopo.so"),
]:
    try:
        supplied = Path(os.environ[var])
        path = supplied.resolve(strict=True)
        if not supplied.is_absolute() or not stat.S_ISREG(path.stat().st_mode) or path.is_relative_to(root):
            raise ValueError("expected an absolute path to a regular file outside the worktree")
        with path.open("rb") as stream:
            header = stream.read(20)
        if not header:
            raise ValueError("file is empty")
        if var != "CAMBRICON_CNDEV_HEADER" and (
            header[:7] != b"\x7fELF\x02\x01\x01" or header[16:20] != b"\x03\x00\x3e\x00"
        ):
            raise ValueError("expected an x86-64 ELF shared object")
        if any(char in str(supplied) for char in [",", '"', "\r", "\n"]):
            raise ValueError("path contains characters unsupported by the build secret argument")
    except (KeyError, OSError, ValueError) as error:
        reason = str(error) if isinstance(error, ValueError) else "file is missing or unreadable"
        print(f"{var} ({name}): {reason}", file=sys.stderr)
        bad = True
if bad:
    sys.exit(1)
print(lock.repository, lock.tag, lock.commit)
PY
)"
if [[ "$mode" == --check-inputs ]]; then
    echo 'Cambricon SDK input files passed presence and architecture checks.'
    exit 0
fi
read -r repository tag commit <<< "$lock"
image="cambricon-device-plugin:$tag"
scratch="$(mktemp -d)"
builder=
container=
cleanup() {
    local status=$?
    if [[ -n "$container" ]]; then
        docker rm -v "$container" >/dev/null 2>&1 || status=1
    fi
    if [[ -n "$builder" ]]; then
        if ! docker buildx rm "$builder" >/dev/null 2>&1; then
            echo 'Failed to remove the temporary BuildKit builder and its state.' >&2
            status=1
        fi
    fi
    rm -rf -- "$scratch"
    return "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

mkdir -p "$scratch/context/source" "$scratch/context/licenses"
GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null git -C "$scratch" init -q
GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 \
    git -C "$scratch" fetch -q --depth=1 "$repository" "$commit"
if [[ "$(git -C "$scratch" rev-parse 'FETCH_HEAD^{commit}')" != "$commit" ]]; then
    echo 'Fetched source did not match the reviewed commit.' >&2
    exit 1
fi
git -C "$scratch" archive "$commit:device-plugin" | tar -xf - -C "$scratch/context/source"
git -C "$scratch" show "$commit:LICENSE" > "$scratch/context/licenses/LICENSE"
if git -C "$scratch" cat-file -e "$commit:NOTICE" 2>/dev/null; then
    git -C "$scratch" show "$commit:NOTICE" > "$scratch/context/licenses/NOTICE"
fi
mkdir -p "$scratch/context/source/pkg/cndev/include"
cp "$recipe/Dockerfile" "$scratch/context/Dockerfile"

# BuildKit may retain intermediate state even when cache reuse is disabled.
builder_name="cambricon-${scratch##*.}-$$"
builder="$(docker buildx create --name "$builder_name" --driver docker-container)"
if ! docker buildx build --builder "$builder" --platform linux/amd64 --no-cache \
    --provenance=false --sbom=false --load --tag "$image" --build-arg "VERSION=$tag" \
    --label "org.opencontainers.image.revision=$commit" \
    --secret "id=cndev_header,src=$CAMBRICON_CNDEV_HEADER" \
    --secret "id=libcndev,src=$CAMBRICON_LIBCNDEV" \
    --secret "id=libcntopo,src=$CAMBRICON_LIBCNTOPO" \
    "$scratch/context" > "$scratch/build.log" 2>&1; then
    echo 'Cambricon image build failed in the authorized environment.' >&2
    exit 1
fi

expected='linux/amd64 ["/usr/bin/k8s-device-plugin"]'
if [[ "$(docker image inspect --format '{{.Os}}/{{.Architecture}} {{json .Config.Cmd}}' "$image")" != "$expected" ]]; then
    echo 'Image platform or startup command did not match the recipe.' >&2
    exit 1
fi
container="$(docker create --platform linux/amd64 "$image")"
docker export "$container" | tar -tf - > "$scratch/files"
for file in usr/bin/k8s-device-plugin usr/lib/libcndev.so usr/lib/libcntopo.so; do
    if ! grep -Fxq "$file" "$scratch/files"; then
        echo "Image is missing $file." >&2
        exit 1
    fi
done
echo "Built and checked $image for linux/amd64 in the authorized Docker daemon."
