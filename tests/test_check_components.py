import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_components import check, inventory
from github import GitHub
from metadata import ROOT, Error, load_local, lock_path, parse_lock

COMPONENT = "cambricon/device-plugin"
HYGON = "hygon/hcu-device-plugin"
OLD = load_local(ROOT, COMPONENT)
OLD_SOURCE = (ROOT / lock_path(COMPONENT)).read_text()
NEW_SOURCE = OLD_SOURCE.replace(OLD.tag, "v2.6.0").replace(OLD.commit, "b" * 40)
NEW = parse_lock(NEW_SOURCE)


class ComponentChecks(unittest.TestCase):
    def test_inventory_and_invalid_lock_are_independent(self):
        self.assertEqual(inventory(ROOT), [COMPONENT, HYGON, "hygon/hcu-exporter"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / lock_path(HYGON)
            path.parent.mkdir(parents=True)
            self.assertEqual(inventory(root), [HYGON])
            with self.assertRaisesRegex(Error, "upstream.yaml is missing"):
                check(root, HYGON, None, None)

    def test_renovate_format_and_existing_validation(self):
        self.assertEqual(parse_lock(f"# Upstream lock\n{OLD_SOURCE.rstrip()} # SHA\n"), OLD)
        lines = OLD_SOURCE.splitlines()
        invalid_sources = [
            OLD_SOURCE + "tag: v3.0.0\n",
            OLD_SOURCE + "extra: value\n",
            OLD_SOURCE.replace(OLD.tag, f"{OLD.tag}-rc.1"),
            OLD_SOURCE.replace("github.com", "git.example.com"),
            OLD_SOURCE.split("commit:")[0],
            OLD_SOURCE.replace(f'"{OLD.commit}"', "1" * 40),
            "\n".join([lines[1], lines[0], lines[2]]),
            "\n".join([lines[0], "# intervening comment", lines[1], lines[2]]),
        ]
        for invalid in invalid_sources:
            with self.subTest(invalid=invalid), self.assertRaises(Error):
                parse_lock(invalid)

    def test_partial_image_recipe_cannot_silently_skip_public_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / lock_path(COMPONENT)
            path.parent.mkdir(parents=True)
            path.write_text(OLD_SOURCE)
            self.assertEqual(check(root, COMPONENT, None, None), OLD)
            path.with_name("Dockerfile").touch()
            with self.assertRaisesRegex(Error, "recipe requires"):
                check(root, COMPONENT, None, None)

    def test_check_requires_published_stable_release(self):
        api = Mock()
        api.tag_commit.return_value = OLD.commit
        stable = {"tag_name": OLD.tag, "draft": False, "prerelease": False}
        for release in [None, stable | {"draft": True}, stable | {"prerelease": True}]:
            with (
                self.subTest(release=release),
                self.assertRaisesRegex(Error, "stable GitHub Release"),
            ):
                api.release.return_value = release
                check(ROOT, COMPONENT, None, api)
        api.release.return_value = stable
        self.assertEqual(check(ROOT, COMPONENT, None, api), OLD)

    def test_pr_update_rechecks_base_tag_and_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / lock_path(COMPONENT)
            path.parent.mkdir(parents=True)
            path.write_text(OLD_SOURCE)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            tree = subprocess.check_output(["git", "write-tree"], cwd=root, text=True).strip()
            base = subprocess.check_output(
                [
                    "git",
                    "-c",
                    "user.name=Fixture",
                    "-c",
                    "user.email=fixture@example.test",
                    "-c",
                    "commit.gpgsign=false",
                    "commit-tree",
                    tree,
                    "-m",
                    "Fixture base",
                ],
                cwd=root,
                text=True,
            ).strip()
            path.write_text(NEW_SOURCE)

            api = Mock()
            api.release.return_value = {"tag_name": NEW.tag, "draft": False, "prerelease": False}
            api.tag_commit.side_effect = ["a" * 40, NEW.commit]
            with self.assertRaisesRegex(Error, f"{OLD.tag} locked at"):
                check(root, COMPONENT, base, api)
            api.tag_commit.assert_called_once_with(OLD.slug, OLD.tag)
            api.release.assert_not_called()

            api.tag_commit.side_effect = [OLD.commit, "a" * 40]
            with self.assertRaisesRegex(Error, f"{NEW.tag} locked at"):
                check(root, COMPONENT, base, api)
            api.tag_commit.side_effect = [OLD.commit, NEW.commit]
            self.assertEqual(check(root, COMPONENT, base, api), NEW)

            path.write_text(OLD_SOURCE.replace(OLD.tag, "v2.4.0"))
            with self.assertRaisesRegex(Error, "must advance"):
                check(root, COMPONENT, base, None)

    @patch.object(GitHub, "api")
    def test_annotated_tag_is_peeled_through_nested_tags(self, api):
        api.side_effect = [
            {"object": {"type": "tag", "sha": "e" * 40}},
            {"object": {"type": "tag", "sha": "f" * 40}},
            {"object": {"type": "commit", "sha": OLD.commit}},
        ]
        self.assertEqual(GitHub().tag_commit(OLD.slug, OLD.tag), OLD.commit)
        self.assertEqual(api.call_count, 3)
