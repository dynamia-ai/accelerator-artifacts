import io
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import components

MIXED = """
version = "v1.2.3"

[artifacts.install]
kind = "helm-chart"
approved_version = "v1.2.3"

[artifacts.main]
kind = "app-image"
approved_version = "v1.2.3"

[artifacts.sidecar]
kind = "app-image"
approved_version = "v1.2.3"
"""


class ComponentTests(unittest.TestCase):
    def setUp(self):
        temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(temporary)
        self.enterContext(patch.object(components, "ROOT", self.root))
        self.directory = self.root / "vendors/vendor/component"
        self.directory.mkdir(parents=True)
        for filename in ("Makefile", "README.md", "LICENSING.md"):
            (self.directory / filename).touch()
        self.config = self.directory / "component.toml"
        self.config.write_text(MIXED)

    def test_inventory_ignores_docs_only_vendor(self):
        readme = self.root / "vendors/cambricon/README.md"
        readme.parent.mkdir()
        readme.touch()
        self.assertEqual([item.name for item in components.inventory()], ["vendor/component"])

    def test_mixed_component_runs_one_make_target_per_kind(self):
        component = components.component("vendor/component")
        directory = self.root / "outputs"
        for name in ("main", "sidecar"):
            path = directory / name / "image-source"
            path.parent.mkdir(parents=True)
            path.write_text(f"docker://example.com/{name}@sha256:{'0' * 64}\n")

        def run(*args, **_kwargs):
            if args[0] == "yq":
                return subprocess.CompletedProcess(args, 0, b'{"name":"install","version":"1.2.3"}')
            return subprocess.CompletedProcess(args, 0, b"")

        with (
            patch.object(components, "run", side_effect=run) as command,
            patch.object(components, "normalize_chart"),
        ):
            components.build(component, directory)
        targets = [call.args[1] for call in command.call_args_list if call.args[0] == "make"]
        self.assertEqual(targets, ["app", "chart"])

    def test_release_requires_current_approval_for_every_artifact(self):
        tag = "refs/tags/release/vendor/component/v1.2.3"
        self.assertEqual(len(components.release_component(tag).artifacts), 3)
        self.config.write_text(MIXED.replace('version = "v1.2.3"', 'version = "v1.2.4"', 1))
        with self.assertRaisesRegex(ValueError, "declares v1.2.4"):
            components.release_component(tag)
        with self.assertRaisesRegex(ValueError, "pending for install, main, sidecar"):
            components.release_component("release/vendor/component/v1.2.4")

    def test_chart_retry_ignores_tar_timestamps_and_order(self):
        paths = [self.root / "first.tgz", self.root / "second.tgz"]
        for timestamp, path in enumerate(paths, start=1):
            entries = ["chart/Chart.yaml", "chart/values.yaml"]
            if timestamp == 2:
                entries.reverse()
            with tarfile.open(path, "w:gz") as archive:
                for name in entries:
                    entry = tarfile.TarInfo(name)
                    entry.mtime = timestamp
                    entry.size = len(name)
                    archive.addfile(entry, io.BytesIO(name.encode()))
            components.normalize_chart(path)

        self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())

    def test_bad_release_tag_cannot_select_a_path(self):
        with self.assertRaisesRegex(ValueError, "Expected release"):
            components.release_component("release/../component/v1.2.3")


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.image = b'{"schemaVersion": 2, "layers":[]}'
        self.image_digest = components.digest(self.image)
        self.image_publication = components.Publication(
            "ghcr.io/example/image",
            "v1.2.3",
            "app-image",
            "oci:/tmp/layout:artifact",
            self.image_digest,
        )

    def test_only_a_missing_manifest_allows_a_push(self):
        source = "docker://ghcr.io/example/image:v1.2.3"
        with patch.object(components.subprocess, "run") as command:
            command.return_value = subprocess.CompletedProcess([], 1, b"", b"manifest unknown")
            self.assertIsNone(components.manifest(source, allow_missing=True))
            command.return_value = subprocess.CompletedProcess([], 1, b"", b"unauthorized")
            with self.assertRaisesRegex(ValueError, "unauthorized"):
                components.manifest(source, allow_missing=True)

    def test_reuse_only_identical_image(self):
        with patch.object(components, "manifest", return_value=self.image):
            self.assertEqual(self.image_publication.inspect(), self.image_digest)
        with (
            patch.object(components, "manifest", return_value=b"different content"),
            self.assertRaisesRegex(ValueError, "existing content differs"),
        ):
            self.image_publication.inspect()

    def test_chart_reuse_compares_chart_layer_and_reports_manifest_digest(self):
        chart = b"chart file"
        raw = json.dumps(
            {"layers": [{"mediaType": components.CHART_LAYER, "digest": components.digest(chart)}]}
        ).encode()
        chart_publication = components.Publication(
            "ghcr.io/example/chart",
            "1.2.3",
            "helm-chart",
            "/tmp/example.tgz",
            components.digest(chart),
        )
        with patch.object(components, "manifest", return_value=raw):
            self.assertEqual(chart_publication.inspect(), components.digest(raw))


if __name__ == "__main__":
    unittest.main()
