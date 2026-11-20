"""Validate component manifests, run Make targets, and publish their outputs."""

import argparse
import gzip
import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "ghcr.io/dynamia-ai/accelerator-artifacts"
TARGETS = {"app-image": "app", "helm-chart": "chart"}
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
VERSION = r"v(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){2,3}"
RELEASE = re.compile(rf"release/(?P<component>{SLUG}/{SLUG})/(?P<version>{VERSION})")
CHART_LAYER = "application/vnd.cncf.helm.chart.content.v1.tar+gzip"


@dataclass(frozen=True)
class Artifact:
    name: str
    kind: str
    approved_version: str | None


@dataclass(frozen=True)
class Component:
    name: str
    directory: Path
    version: str
    artifacts: tuple[Artifact, ...]


def component(name: str) -> Component:
    if not re.fullmatch(rf"{SLUG}/{SLUG}", name):
        raise ValueError(f"Invalid component name: {name}")
    directory = ROOT / "vendors" / name
    for filename in ("README.md", "LICENSING.md", "Makefile", "component.toml"):
        if not (directory / filename).is_file():
            raise ValueError(f"{name}: missing {filename}")

    config = tomllib.loads((directory / "component.toml").read_text())
    version = config.get("version")
    artifacts = config.get("artifacts")
    if not isinstance(version, str) or not re.fullmatch(VERSION, version):
        raise ValueError(f"{name}: expected a version such as v1.2.3")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError(f"{name}: declare at least one artifact")
    if "upstream" in config and (
        not isinstance(config["upstream"], str)
        or not re.fullmatch(r"[\w.-]+/[\w.-]+", config["upstream"])
    ):
        raise ValueError(f"{name}: upstream must be a GitHub owner/repository")

    result = []
    for artifact, fields in artifacts.items():
        if not re.fullmatch(SLUG, artifact) or not isinstance(fields, dict):
            raise ValueError(f"{name}: invalid artifact {artifact}")
        kind = fields.get("kind")
        approved_version = fields.get("approved_version")
        if kind not in ("app-image", "helm-chart") or set(fields) - {"kind", "approved_version"}:
            raise ValueError(f"{name}/{artifact}: expected kind and optional approved_version")
        if approved_version is not None and (
            not isinstance(approved_version, str) or not re.fullmatch(VERSION, approved_version)
        ):
            raise ValueError(f"{name}/{artifact}: invalid approved_version")
        if kind == "helm-chart" and version.count(".") != 2:
            raise ValueError(f"{name}/{artifact}: a chart requires a three-part version")
        result.append(Artifact(artifact, kind, approved_version))
    return Component(name, directory, version, tuple(result))


def inventory():
    vendors = ROOT / "vendors"
    paths = {
        path.parent
        for file in ("component.toml", "Makefile")
        for path in vendors.glob(f"*/*/{file}")
    }
    return [component(path.relative_to(vendors).as_posix()) for path in sorted(paths)]


def release_component(tag: str) -> Component:
    match = RELEASE.fullmatch(tag.removeprefix("refs/tags/"))
    if not match:
        raise ValueError("Expected release/<vendor>/<component>/<version>")
    selected = component(match["component"])
    if selected.version != match["version"]:
        raise ValueError(f"{tag}: the component declares {selected.version}")
    pending = [
        artifact.name
        for artifact in selected.artifacts
        if artifact.approved_version != selected.version
    ]
    if pending:
        raise ValueError(f"{selected.name}: public redistribution pending for {', '.join(pending)}")
    return selected


def output(selected: Component, artifact: Artifact, directory: Path) -> Path:
    folder = directory / artifact.name
    if artifact.kind == "app-image":
        return folder / "image-source"
    return folder / f"{artifact.name}-{selected.version[1:]}.tgz"


def run(*args: str, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def image_source(path: Path) -> str:
    source = path.read_text().strip()
    if re.fullmatch(r"docker://[^\s@]+@sha256:[0-9a-f]{64}", source):
        return source
    if not source.startswith(f"oci:{path.parent}/") or "\n" in source:
        raise ValueError(f"{path}: expected a local OCI layout or a digest-pinned registry image")
    return source


def normalize_chart(path: Path) -> None:
    # Helm tar headers can include the current time, even for identical chart files.
    normalized = path.with_suffix(".tmp")
    with (
        tarfile.open(path, "r:gz") as source,
        normalized.open("wb") as output,
        gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as target,
    ):
        for member in sorted(source.getmembers(), key=lambda item: item.name):
            member.mtime = 0
            member.pax_headers.pop("mtime", None)
            if member.isfile():
                with source.extractfile(member) as contents:
                    target.addfile(member, contents)
            else:
                target.addfile(member)
    normalized.replace(path)


def build(selected: Component, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for kind, target in TARGETS.items():
        if any(artifact.kind == kind for artifact in selected.artifacts):
            run("make", target, f"OUTPUT_DIR={directory}", cwd=selected.directory)
    for artifact in selected.artifacts:
        path = output(selected, artifact, directory)
        if artifact.kind == "app-image":
            run("skopeo", "inspect", "--raw", image_source(path), stdout=subprocess.DEVNULL)
        else:
            metadata = run("helm", "show", "chart", str(path), capture_output=True).stdout
            chart = json.loads(
                run("yq", "-o=json", ".", input=metadata, capture_output=True).stdout
            )
            if (chart["name"], chart["version"]) != (artifact.name, selected.version[1:]):
                raise ValueError(f"{path}: Chart name or version differs from component manifest")
            normalize_chart(path)


def digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def manifest(source: str, *, allow_missing: bool = False) -> bytes | None:
    result = subprocess.run(
        ("skopeo", "inspect", "--raw", source), check=False, capture_output=True
    )
    if result.returncode == 0:
        return result.stdout
    error = result.stderr.decode(errors="replace").strip()
    if allow_missing and re.search(r"manifest unknown|name unknown", error, re.IGNORECASE):
        return None
    raise ValueError(f"{source}: {error}")


@dataclass(frozen=True)
class Publication:
    repository: str
    version: str
    kind: str
    source: str
    content_digest: str

    @property
    def reference(self) -> str:
        return f"{self.repository}:{self.version}"

    def inspect(self, *, allow_missing: bool = False) -> str | None:
        raw = manifest(f"docker://{self.reference}", allow_missing=allow_missing)
        if raw is None:
            return None
        if self.kind == "helm-chart":
            layers = json.loads(raw).get("layers", [])
            contents = [layer["digest"] for layer in layers if layer["mediaType"] == CHART_LAYER]
            identical = contents == [self.content_digest]
        else:
            identical = digest(raw) == self.content_digest
        if not identical:
            raise ValueError(
                f"{self.reference}: existing content differs from the prepared artifact"
            )
        return digest(raw)

    def push(self) -> None:
        if self.kind == "app-image":
            run(
                "skopeo",
                "copy",
                "--all",
                "--preserve-digests",
                self.source,
                f"docker://{self.reference}",
            )
        else:
            run("helm", "push", self.source, f"oci://{self.repository.rsplit('/', 1)[0]}")


def publish(selected: Component, directory: Path) -> list[str]:
    publications = []
    for artifact in selected.artifacts:
        path = output(selected, artifact, directory)
        base = f"{REGISTRY}/{selected.name}"
        if artifact.kind == "app-image":
            source = image_source(path)
            raw = manifest(source)
            publications.append(
                Publication(
                    f"{base}/images/{artifact.name}",
                    selected.version,
                    artifact.kind,
                    source,
                    digest(raw),
                )
            )
        else:
            publications.append(
                Publication(
                    f"{base}/charts/{artifact.name}",
                    selected.version[1:],
                    artifact.kind,
                    str(path),
                    digest(path.read_bytes()),
                )
            )

    existing = [item.inspect(allow_missing=True) for item in publications]
    records = []
    for item, published_digest in zip(publications, existing, strict=True):
        if published_digest is None:
            item.push()
            published_digest = item.inspect()
        reference = f"{item.repository}@{published_digest}"
        if item.kind == "helm-chart":
            reference = f"oci://{reference}"
        record = f"`{item.reference}` → `{reference}`"
        print(record, flush=True)
        records.append(record)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("matrix")
    check = commands.add_parser("build")
    check.add_argument("component")
    release = commands.add_parser("publish")
    release.add_argument("tag")
    release.add_argument("--summary", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "matrix":
            print(json.dumps([item.name for item in inventory()]))
            return
        selected = (
            component(args.component) if args.command == "build" else release_component(args.tag)
        )
        with tempfile.TemporaryDirectory(prefix="accelerator-artifacts-") as temporary:
            directory = Path(temporary)
            build(selected, directory)
            if args.command == "publish":
                records = publish(selected, directory)
                if args.summary:
                    with args.summary.open("a") as summary:
                        summary.write("\n".join(f"- {record}" for record in records) + "\n")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
