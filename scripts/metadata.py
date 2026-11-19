"""Discover components and validate their reviewed source locks and build recipes."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "dynamia-ai/accelerator-artifacts"
COMPONENT = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*/[a-z0-9]+(?:-[a-z0-9]+)*")
GITHUB_REPO = re.compile(
    r"https://github\.com/[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_][A-Za-z0-9_.-]*"
)
TAG = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
SHA = re.compile(r"[a-f0-9]{40}")
FIELDS = {"repository": GITHUB_REPO, "tag": TAG, "commit": SHA}
PLATFORM = re.compile(r"linux/(amd64|arm64)")
BUILD_FILES = ("build.sh", "Dockerfile", "platform")
# The lock format uses a flat YAML mapping with plain or quoted literal strings.
LINE = re.compile(
    r"""(?P<key>[a-z]+):[ \t]+(?P<value>"[^"]*"|'[^']*'|[^ \t#]+)(?:[ \t]+(?:#.*)?)?"""
)


class Error(Exception):
    """An expected validation or service failure."""


def version(tag):
    return tuple(map(int, TAG.fullmatch(tag).groups()))


@dataclass(frozen=True)
class Lock:
    repository: str
    tag: str
    commit: str

    @property
    def slug(self):
        return self.repository.removeprefix("https://github.com/")

    @property
    def version(self):
        return version(self.tag)


def lock_path(component):
    if not COMPONENT.fullmatch(component):
        raise Error("invalid component identifier")
    return f"vendors/{component}/upstream.yaml"


def parse_lock(source):
    fields = {}
    positions = []
    for index, line in enumerate(source.splitlines()):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = LINE.fullmatch(line)
        if not match:
            raise Error("expected a flat mapping of literal strings")
        key, value = match.group("key", "value")
        if key not in FIELDS or key in fields:
            raise Error(f"unknown or duplicate field: {key}")
        # An unquoted, all-numeric SHA is a YAML number, not a string.
        if value[0] in "\"'":
            value = value[1:-1]
        elif key == "commit" and re.fullmatch(r"[0-9]+(?:e[0-9]+)?", value):
            raise Error("commit must be a string")
        if not FIELDS[key].fullmatch(value) or (key == "repository" and value.endswith(".git")):
            raise Error(f"invalid {key}")
        fields[key] = value
        positions.append(index)
    if fields.keys() != FIELDS.keys():
        raise Error("repository, tag and commit are required")
    if tuple(fields) != tuple(FIELDS) or positions[-1] - positions[0] != 2:
        raise Error("repository, tag and commit must be in order on three consecutive lines")
    return Lock(**fields)


def components(root):
    vendors = root / "vendors"
    if vendors.is_symlink() or not vendors.is_dir():
        raise Error("vendors must be a directory")
    for vendor in sorted(vendors.iterdir()):
        if vendor.is_symlink():
            raise Error(f"unexpected symlink in vendors: {vendor.name}")
        if not vendor.is_dir():
            continue
        for directory in sorted(vendor.iterdir()):
            if directory.is_symlink():
                raise Error(f"unexpected symlink in vendor: {vendor.name}")
            if directory.is_dir():
                yield f"{vendor.name}/{directory.name}"


def load_local(root, component):
    path = root / lock_path(component)
    if any(directory.is_symlink() for directory in path.parents[:3]):
        raise Error("component directories must not be symlinks")
    if path.is_symlink() or not path.is_file():
        raise Error("upstream.yaml is missing or is not a regular file")
    return parse_lock(path.read_text(encoding="utf-8"))


def build_platform(root, component):
    directory = (root / lock_path(component)).parent
    files = [directory / name for name in BUILD_FILES]
    if not any(path.exists() or path.is_symlink() for path in files):
        return None
    if any(path.is_symlink() or not path.is_file() for path in files):
        raise Error("image recipe requires regular build.sh, Dockerfile and platform files")
    platform = (directory / "platform").read_text(encoding="utf-8").strip()
    if not PLATFORM.fullmatch(platform):
        raise Error("image recipe platform must be linux/amd64 or linux/arm64")
    return platform


def read_base_lock(root, component, base):
    path = lock_path(component)
    listing = subprocess.run(
        ["git", "ls-tree", base, "--", path],
        cwd=root,
        check=True,
        capture_output=True,
    )
    if not listing.stdout:
        return None
    return parse_lock(
        subprocess.run(
            ["git", "show", f"{base}:{path}"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout
    )
