import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import components, update_amd


class ImagePinTests(unittest.TestCase):
    def setUp(self):
        temporary = self.enterContext(tempfile.TemporaryDirectory())
        root = Path(temporary)
        self.enterContext(patch.object(components, "ROOT", root))
        self.directory = root / update_amd.DIRECTORY
        self.directory.mkdir(parents=True)
        self.previous_manifest = 'version = "v1.5.3"\n'
        self.image = "docker.io/rocm/device-metrics-exporter"
        self.old_digest = "sha256:" + "1" * 64
        self.new_digest = "sha256:" + "2" * 64
        self.previous_makefile = f"APP_IMAGE := {self.image}\nAPP_DIGEST := {self.old_digest}\n"
        (self.directory / "Makefile").write_text(self.previous_makefile)
        (self.directory / "component.toml").write_text(self.previous_manifest)

    def previous_files(self, *args, **kwargs):
        contents = (
            self.previous_manifest if args[2].endswith("component.toml") else self.previous_makefile
        )
        return subprocess.CompletedProcess(args, 0, contents)

    def test_unchanged_pin_does_not_resolve_tag(self):
        with (
            patch.object(components, "run", side_effect=self.previous_files),
            patch.object(update_amd, "image_digest") as lookup,
        ):
            update_amd.check_pin("HEAD^1")

        lookup.assert_not_called()

    def test_version_change_requires_digest_from_upstream_tag(self):
        (self.directory / "component.toml").write_text('version = "v1.5.4"\n')
        with (
            patch.object(components, "run", side_effect=self.previous_files),
            patch.object(update_amd, "image_digest", return_value=self.new_digest),
        ):
            with self.assertRaisesRegex(ValueError, "v1.5.4 resolves to .* but APP_DIGEST is"):
                update_amd.check_pin("HEAD^1")

            (self.directory / "Makefile").write_text(
                self.previous_makefile.replace(self.old_digest, self.new_digest)
            )
            update_amd.check_pin("HEAD^1")
