#!/usr/bin/env bash
set -euo pipefail

url=${1:?supply an archive URL}
checksum=${2:?supply the archive SHA-256}
output=${3:?supply the artifact directory}
platform=${4:?supply the expected platform}

mkdir -p "$output"
archive=$(mktemp "$output/upstream.XXXXXX")
trap 'rm -f "$archive"' EXIT

curl --fail --silent --show-error --location --retry 3 --output "$archive" "$url"
printf '%s  %s\n' "$checksum" "$archive" | shasum -a 256 --check
source="oci:$output/image:artifact"
skopeo copy --all "docker-archive:$archive" "$source"
actual_platform=$(skopeo inspect --format '{{.Os}}/{{.Architecture}}' "$source")
if [[ "$actual_platform" != "$platform" ]]; then
    printf 'Expected image platform %s, got %s\n' "$platform" "$actual_platform" >&2
    exit 1
fi
printf '%s\n' "$source" > "$output/image-source"
