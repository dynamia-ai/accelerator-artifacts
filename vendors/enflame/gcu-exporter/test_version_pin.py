import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

COMPONENT = Path(__file__).resolve().parent
ROOT = COMPONENT.parents[2]


class VersionPinTest(unittest.TestCase):
    def test_pinned_version_passes_make_validation(self):
        result = self.dry_run(COMPONENT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--tag "gcu-exporter:v3.6.5"', result.stdout)

    def test_unconfigured_manifest_version_stops_before_buildx(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            component = root / COMPONENT.relative_to(ROOT)
            component.mkdir(parents=True)
            shutil.copyfile(COMPONENT / "Makefile", component / "Makefile")
            (root / "scripts").mkdir()
            shutil.copyfile(ROOT / "scripts/component.mk", root / "scripts/component.mk")
            (component / "component.toml").write_text('version = "v3.6.6"\n')
            result = self.dry_run(component)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No gcu-exporter source pin for v3.6.6", result.stderr)
        self.assertNotIn("docker buildx", result.stdout)

    def test_command_line_version_override_stops_before_buildx(self):
        result = self.dry_run(COMPONENT, "VERSION=v3.6.6")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Set the gcu-exporter version in component.toml", result.stderr)
        self.assertNotIn("docker buildx", result.stdout)

    @staticmethod
    def dry_run(component, *args):
        return subprocess.run(
            ["make", "-n", "app", *args], cwd=component, capture_output=True, text=True, check=False
        )
