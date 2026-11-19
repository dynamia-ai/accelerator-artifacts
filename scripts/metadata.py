"""Validate the flat upstream.yaml schema and preserve its formatting on updates."""

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
    for line in source.splitlines():
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
    if fields.keys() != FIELDS.keys():
        raise Error("repository, tag and commit are required")
    return Lock(**fields)


def update_lock(source, candidate):
    previous = parse_lock(source)
    if previous.repository != candidate.repository or previous.version >= candidate.version:
        raise Error("lock update must advance the version in the same repository")
    for field in ("tag", "commit"):
        pattern = re.compile(rf"^({field}:[ \t]+)(?:\"[^\"]*\"|'[^']*'|[^ \t\r\n#]+)", re.MULTILINE)
        value = getattr(candidate, field)
        source = pattern.sub(lambda match, value=value: f'{match[1]}"{value}"', source)
    if parse_lock(source) != candidate:
        raise Error("generated lock did not match the candidate")
    return source


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
    if path.is_symlink() or not path.is_file():
        raise Error("upstream.yaml is missing or is not a regular file")
    return parse_lock(path.read_text(encoding="utf-8"))


def check_base(root, component, lock, base, automatic_head):
    path = lock_path(component)
    listing = subprocess.run(
        ["git", "ls-tree", base, "--", path],
        cwd=root,
        check=True,
        capture_output=True,
    )
    if not listing.stdout:
        if automatic_head:
            raise Error("automatic updates require an existing lock on main")
        return
    previous = parse_lock(
        subprocess.run(
            ["git", "show", f"{base}:{path}"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    if lock.repository == previous.repository and lock.version < previous.version:
        raise Error("version regresses from the base")
    if automatic_head:
        branch = f"upstream/{component}/{lock.tag}"
        if (
            automatic_head != branch
            or lock.repository != previous.repository
            or lock.version <= previous.version
        ):
            raise Error("automatic update must advance the same upstream and match its head branch")
