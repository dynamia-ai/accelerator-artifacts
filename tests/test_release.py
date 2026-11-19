import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from metadata import REPOSITORY, ROOT, Error, load_local, lock_path
from record_release import attach
from release import (
    RECIPE_FILES,
    RELEASE_CONTROLS,
    WORKFLOW,
    ReleaseTarget,
    ghcr_auth,
    licensing_digest,
    platform_digests,
    preflight,
    raw_manifest,
    run,
    transfer,
    verify_evidence,
)

COMPONENT = "cambricon/device-plugin"
PLATFORM = "linux/amd64"
RECIPE = "1" * 40
RELEASE_TAG = "release/cambricon/device-plugin/v2.5.0"
CONTEXT = {
    "GITHUB_ACTIONS": "true",
    "GITHUB_REPOSITORY": REPOSITORY,
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_WORKFLOW_REF": f"{WORKFLOW}@refs/heads/main",
    "RELEASE_REF": RELEASE_TAG,
    "RELEASE_ENVIRONMENT": "public-ghcr-cambricon--device-plugin",
    "PUBLIC_RELEASE_ENABLED": "true",
    "GITHUB_SHA": RECIPE,
}
SOURCE = "private.test/staging/device-plugin"
DESTINATION = "ghcr.io/dynamia-ai/accelerator-artifacts/cambricon/device-plugin"
MANIFEST = b'{"schemaVersion":2,"layers":[]}'
DIGEST = "sha256:" + hashlib.sha256(MANIFEST).hexdigest()


def release_fixture(root, status, component=COMPONENT, platform=PLATFORM):
    component_path = root / lock_path(component)
    component_path.parent.mkdir(parents=True)
    public_path = ROOT / lock_path(COMPONENT)
    for name in RECIPE_FILES:
        if name == "LICENSING.md":
            continue
        destination = component_path.with_name(name)
        if name == "platform":
            destination.write_text(platform + "\n")
        else:
            original = (
                ROOT / lock_path(component)
                if name == "upstream.yaml"
                else public_path.with_name(name)
            )
            destination.write_bytes(original.read_bytes())
    for name in RELEASE_CONTROLS:
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    lock = load_local(root, component)
    component_path.with_name("LICENSING.md").write_text(
        f"Upstream-Tag: {lock.tag}\nPublic-Redistribution: {status}\n"
    )
    return lock


class ReleaseTests(unittest.TestCase):
    def test_pending_licensing_and_untrusted_context_refuse_before_external_calls(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("release.GitHub") as api,
            patch("release.ghcr_auth") as auth,
        ):
            root = Path(directory)
            output = root / "record.json"
            release_fixture(root, "pending")
            with self.assertRaisesRegex(Error, "release tag push or a retry from main"):
                run(CONTEXT | {"GITHUB_EVENT_NAME": "pull_request"}, output, root)
            with self.assertRaisesRegex(Error, "not approved"):
                run(CONTEXT, output, root)
            self.assertFalse(output.exists())
            api.assert_not_called()
            auth.assert_not_called()

    def test_ghcr_auth_uses_only_the_workflow_actor_and_token(self):
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            with self.assertRaisesRegex(Error, "GITHUB_ACTOR"):
                ghcr_auth({"GH_TOKEN": "synthetic-token"}, scratch)
            self.assertEqual(list(scratch.iterdir()), [])
            auth = ghcr_auth(
                {"GITHUB_ACTOR": "workflow-actor", "GH_TOKEN": "synthetic-token"}, scratch
            )
            credentials = json.loads(auth.read_bytes())["auths"]
            self.assertEqual(set(credentials), {"ghcr.io"})
            self.assertEqual(
                base64.b64decode(credentials["ghcr.io"]["auth"]), b"workflow-actor:synthetic-token"
            )

    @patch("release.subprocess.run")
    def test_missing_ghcr_package_does_not_treat_auth_errors_as_absence(self, process):
        ref = f"{DESTINATION}:v2.5.0"
        auth = Path("unused-auth.json")
        for error in (b"NAME_UNKNOWN: repository name not known", b"manifest unknown"):
            with self.subTest(error=error):
                process.return_value = subprocess.CompletedProcess([], 1, b"", error)
                self.assertIsNone(raw_manifest(ref, auth, missing_ok=True))
        process.return_value = subprocess.CompletedProcess([], 1, b"", b"unauthorized")
        with self.assertRaisesRegex(Error, "manifest inspection failed"):
            raw_manifest(ref, auth, missing_ok=True)

    @patch("release.transfer")
    @patch("release.ghcr_auth")
    @patch("release.verify_evidence")
    @patch("release.GitHub")
    def test_approved_release_resumes_after_unrelated_main_updates(
        self, github, evidence, auth, transfer_mock
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "record.json"
            lock = release_fixture(root, "approved")
            api = github.return_value
            api.main.return_value = "5" * 40
            api.tag_commit.return_value = RECIPE
            api.is_ancestor.return_value = True
            api.file_at.side_effect = lambda path, revision: (root / path).read_text()
            evidence.return_value = {"source_repository": SOURCE, "digest": DIGEST}
            transfer_mock.return_value = [{"platform": "linux/amd64", "manifest_digest": DIGEST}]
            env = CONTEXT | {
                "GH_TOKEN": "synthetic-token",
                "GITHUB_ACTOR": "workflow-actor",
                "STAGING_AUTH": json.dumps({"auths": {"private.test": {"auth": "synthetic"}}}),
            }
            run(env, output, root)
            text = output.read_text()
            self.assertNotIn(SOURCE, text)
            self.assertNotIn("synthetic", text)
            record = json.loads(text)
            self.assertEqual(record["recipe_commit"], RECIPE)
            self.assertEqual(record["image"], f"{DESTINATION}:{lock.tag}")
            self.assertEqual(record["digest"], DIGEST)
            auth.assert_called_once()
            self.assertEqual(transfer_mock.call_args.args[1], DESTINATION)

            for changed in (
                lock_path(COMPONENT).replace("upstream.yaml", "LICENSING.md"),
                ".github/workflows/release.yml",
                ".python-version",
                "scripts/record_release.py",
            ):
                with self.subTest(changed=changed):
                    api.file_at.side_effect = lambda path, revision, changed=changed: (
                        "changed on main" if path == changed else (root / path).read_text()
                    )
                    transfer_mock.reset_mock()
                    auth.reset_mock()
                    with self.assertRaisesRegex(Error, "have changed on main"):
                        run(env, output, root)
                    auth.assert_not_called()
                    transfer_mock.assert_not_called()

    @patch("release.GitHub")
    def test_requires_existing_project_tag_at_an_approved_recipe(self, github):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = release_fixture(root, "approved")
            api = github.return_value
            env = CONTEXT | {"GH_TOKEN": "read"}
            api.tag_commit.return_value = None
            with self.assertRaisesRegex(Error, "must already exist"):
                preflight(env, root)
            api.tag_commit.assert_called_once_with(REPOSITORY, RELEASE_TAG)
            api.main.assert_not_called()

            api.tag_commit.return_value = "5" * 40
            tag_env = env | {
                "GITHUB_EVENT_NAME": "push",
                "GITHUB_REF": f"refs/tags/{RELEASE_TAG}",
                "RELEASE_REF": f"refs/tags/{RELEASE_TAG}",
                "GITHUB_WORKFLOW_REF": f"{WORKFLOW}@refs/tags/{RELEASE_TAG}",
            }
            with self.assertRaisesRegex(Error, "no longer points to the triggering commit"):
                preflight(tag_env, root)

            api.tag_commit.return_value = RECIPE
            api.main.return_value = RECIPE
            api.is_ancestor.return_value = False
            with self.assertRaisesRegex(Error, "reviewed commit on main"):
                preflight(tag_env, root)
            api.is_ancestor.return_value = True
            self.assertEqual(preflight(tag_env, root).lock, lock)

    @patch("release.GitHub")
    def test_main_retry_keeps_the_existing_tag_recipe_sha(self, github):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release_fixture(root, "approved")
            api = github.return_value
            main = "5" * 40
            api.tag_commit.return_value = RECIPE
            api.main.return_value = main
            api.is_ancestor.return_value = True
            api.file_at.side_effect = lambda path, revision: (root / path).read_text()
            for ref in (RELEASE_TAG, f"refs/tags/{RELEASE_TAG}"):
                with self.subTest(ref=ref):
                    env = CONTEXT | {"GH_TOKEN": "read", "GITHUB_SHA": main, "RELEASE_REF": ref}
                    self.assertEqual(preflight(env, root).recipe_commit, RECIPE)
            self.assertTrue(all(call.args[1] == RECIPE for call in api.file_at.call_args_list))

    @patch("release.GitHub")
    def test_retry_rejects_nonrelease_refs_and_nonmain_workflows(self, github):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release_fixture(root, "approved")
            env = CONTEXT | {"GH_TOKEN": "read"}
            for ref in (
                "main",
                "refs/heads/main",
                RECIPE,
                "refs/tags/release/cambricon/device-plugin/v2.6.0",
            ):
                with (
                    self.subTest(ref=ref),
                    self.assertRaisesRegex(Error, "release ref must name a project release tag"),
                ):
                    preflight(env | {"RELEASE_REF": ref}, root)
            with self.assertRaisesRegex(Error, "retry from main"):
                preflight(
                    env
                    | {
                        "GITHUB_REF": "refs/heads/feature",
                        "GITHUB_WORKFLOW_REF": f"{WORKFLOW}@refs/heads/feature",
                    },
                    root,
                )
            github.assert_not_called()

    @patch("release.GitHub")
    def test_routes_two_components_to_distinct_publish_targets(self, github):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hygon = "hygon/hcu-device-plugin"
            hygon_tag = f"release/{hygon}/v3.0.2"
            cambricon_lock = release_fixture(root, "approved")
            hygon_lock = release_fixture(root, "approved", hygon, "linux/arm64")
            api = github.return_value
            api.main.return_value = RECIPE
            api.tag_commit.return_value = RECIPE
            api.is_ancestor.return_value = True
            env = CONTEXT | {"GH_TOKEN": "read"}

            cambricon = preflight(env, root)
            second = preflight(env | {"RELEASE_REF": f"refs/tags/{hygon_tag}"}, root)

            self.assertEqual((cambricon.component, second.component), (COMPONENT, hygon))
            self.assertEqual((cambricon.lock, second.lock), (cambricon_lock, hygon_lock))
            self.assertEqual((cambricon.platform, second.platform), (PLATFORM, "linux/arm64"))
            self.assertEqual(cambricon.image, DESTINATION)
            self.assertEqual(second.image, f"ghcr.io/{REPOSITORY}/{hygon}")
            self.assertEqual(second.environment, "public-ghcr-hygon--hcu-device-plugin")
            with self.assertRaisesRegex(Error, "component release environment"):
                run(env | {"RELEASE_REF": hygon_tag}, root / "record.json", root)
            self.assertFalse((root / "record.json").exists())

    @patch("release.GitHub")
    def test_lock_only_component_cannot_enter_publisher(self, github):
        with self.assertRaisesRegex(Error, "no publication recipe"):
            preflight(CONTEXT | {"RELEASE_REF": "release/hygon/hcu-exporter/v3.0.2"})
        github.assert_not_called()

    @patch("release.quiet")
    def test_manifest_platform_is_checked_against_component_platform(self, quiet):
        quiet.return_value = b'{"os":"linux","architecture":"arm64"}'
        auth = Path("unused-auth.json")
        self.assertEqual(
            platform_digests(SOURCE, MANIFEST, auth, "linux/arm64"),
            [{"platform": "linux/arm64", "manifest_digest": DIGEST}],
        )
        with self.assertRaisesRegex(Error, "recipe platform"):
            platform_digests(SOURCE, MANIFEST, auth, "linux/amd64")

    def test_licensing_approval_must_be_unique_and_version_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / lock_path(COMPONENT)
            path.parent.mkdir(parents=True)
            license_file = path.with_name("LICENSING.md")
            content = b"Upstream-Tag: v2.5.0\nPublic-Redistribution: approved\n"
            license_file.write_bytes(content)
            self.assertEqual(
                licensing_digest(root, COMPONENT, "v2.5.0"), hashlib.sha256(content).hexdigest()
            )
            with self.assertRaises(Error):
                licensing_digest(root, COMPONENT, "v2.6.0")
            license_file.write_bytes(content + b"Public-Redistribution: pending\n")
            with self.assertRaises(Error):
                licensing_digest(root, COMPONENT, "v2.5.0")

    def test_evidence_is_signed_and_bound_to_reviewed_recipe(self):
        lock = load_local(ROOT, COMPONENT)
        license_sha = "3" * 64
        target = ReleaseTarget(COMPONENT, RELEASE_TAG, lock, PLATFORM, license_sha, RECIPE)
        proof = {
            "component": COMPONENT,
            "upstream_repository": lock.repository,
            "upstream_tag": lock.tag,
            "upstream_commit": lock.commit,
            "recipe_commit": RECIPE,
            "licensing_sha256": license_sha,
            "builder": "authorized-builder",
            "platform": "linux/amd64",
            "source_repository": SOURCE,
            "digest": DIGEST,
        }
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            private = scratch / "throwaway-private.pem"
            signed = scratch / "proof.json"
            signed.write_text(json.dumps(proof))
            subprocess.run(
                [
                    "openssl",
                    "genpkey",
                    "-algorithm",
                    "RSA",
                    "-pkeyopt",
                    "rsa_keygen_bits:2048",
                    "-out",
                    str(private),
                ],
                check=True,
                capture_output=True,
            )
            public = subprocess.check_output(
                ["openssl", "pkey", "-in", str(private), "-pubout"]
            ).decode()
            signature = subprocess.check_output(
                ["openssl", "dgst", "-sha256", "-sign", str(private), str(signed)]
            )
            env = CONTEXT | {
                "STAGING_EVIDENCE": signed.read_text(),
                "STAGING_BUILDER": proof["builder"],
                "STAGING_SIGNATURE": base64.b64encode(signature).decode(),
                "STAGING_BUILDER_PUBLIC_KEY": public,
                "STAGING_IMAGE_REPOSITORY": SOURCE,
            }
            self.assertEqual(verify_evidence(env, scratch, target), proof)
            with self.assertRaisesRegex(Error, "signature"):
                verify_evidence(
                    env | {"STAGING_EVIDENCE": signed.read_text() + " "}, scratch, target
                )
            with self.assertRaisesRegex(Error, "reviewed recipe"):
                verify_evidence(
                    env,
                    scratch,
                    ReleaseTarget(COMPONENT, RELEASE_TAG, lock, PLATFORM, license_sha, "4" * 40),
                )

    @patch("release.quiet")
    @patch("release.platform_digests")
    @patch("release.raw_manifest")
    def test_publication_copies_by_digest_and_requires_anonymous_pull(
        self, manifest, platforms, quiet
    ):
        manifest.side_effect = [MANIFEST, None, MANIFEST, MANIFEST]
        platforms.return_value = [{"platform": "linux/amd64", "manifest_digest": DIGEST}]
        pre_write = Mock()
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            transfer(
                SOURCE,
                DESTINATION,
                "v2.5.0",
                DIGEST,
                scratch / "stage",
                scratch / "dest",
                scratch,
                pre_write,
                platform=PLATFORM,
            )
            self.assertEqual(json.loads((scratch / "anonymous.json").read_bytes()), {"auths": {}})
        pre_write.assert_called_once()
        copy, pull = quiet.call_args_list
        self.assertIn("--all", copy.args[0])
        self.assertIn("--preserve-digests", copy.args[0])
        self.assertEqual(
            copy.args[0][-2:], [f"docker://{SOURCE}@{DIGEST}", f"docker://{DESTINATION}:v2.5.0"]
        )
        self.assertIn(f"docker://{DESTINATION}@{DIGEST}", pull.args[0])
        self.assertNotIn(
            "--preserve-digests",
            pull.args[0],
            "the scratch OCI layout must permit conversion from Docker schema 2",
        )
        self.assertNotIn("REGISTRY_AUTH_FILE", pull.kwargs["env"])
        self.assertTrue(manifest.call_args_list[-1].kwargs["env"])

    @patch("release.quiet")
    @patch("release.platform_digests")
    @patch("release.raw_manifest")
    def test_existing_same_digest_is_reverified_and_conflicting_tag_is_preserved(
        self, manifest, platforms, quiet
    ):
        pre_write = Mock()
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            manifest.side_effect = [MANIFEST, MANIFEST, MANIFEST, MANIFEST]
            transfer(
                SOURCE,
                DESTINATION,
                "v2.5.0",
                DIGEST,
                scratch / "stage",
                scratch / "dest",
                scratch,
                pre_write,
                platform=PLATFORM,
            )
            quiet.assert_called_once()
            self.assertEqual(quiet.call_args.args[1], "pull public image anonymously")
            manifest.side_effect = [MANIFEST, b'{"schemaVersion":2}']
            quiet.reset_mock()
            with self.assertRaisesRegex(Error, "different digest"):
                transfer(
                    SOURCE,
                    DESTINATION,
                    "v2.5.0",
                    DIGEST,
                    scratch / "stage",
                    scratch / "dest",
                    scratch,
                    pre_write,
                    platform=PLATFORM,
                )
            quiet.assert_not_called()
        pre_write.assert_not_called()

    @patch("release.quiet")
    @patch("release.platform_digests")
    @patch("release.raw_manifest")
    def test_private_ghcr_version_requires_visibility_before_recording(
        self, manifest, platforms, quiet
    ):
        manifest.side_effect = [MANIFEST, None, Error("image manifest inspection failed")]
        platforms.return_value = [{"platform": "linux/amd64", "manifest_digest": DIGEST}]
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            with self.assertRaisesRegex(Error, "verify package visibility"):
                transfer(
                    SOURCE,
                    DESTINATION,
                    "v2.5.0",
                    DIGEST,
                    scratch / "stage",
                    scratch / "dest",
                    scratch,
                    Mock(),
                    platform=PLATFORM,
                )
        quiet.assert_called_once()
        self.assertIn(f"docker://{DESTINATION}:v2.5.0", quiet.call_args.args[0])

    @patch("release.quiet")
    @patch("release.platform_digests")
    @patch("release.raw_manifest")
    def test_mismatched_staging_bytes_never_reach_destination(self, manifest, platforms, quiet):
        manifest.return_value = b"unexpected"
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            with self.assertRaisesRegex(Error, "staging digest"):
                transfer(
                    SOURCE,
                    DESTINATION,
                    "v2.5.0",
                    DIGEST,
                    scratch / "stage",
                    scratch / "dest",
                    scratch,
                    Mock(),
                    platform=PLATFORM,
                )
        manifest.assert_called_once()
        quiet.assert_not_called()
        platforms.assert_not_called()

    @patch("record_release.run_gh")
    @patch("record_release.GitHub")
    @patch("record_release.preflight")
    def test_record_reuses_existing_attachment_and_refuses_different_content(
        self, preflight, github, gh
    ):
        lock = load_local(ROOT, COMPONENT)
        preflight.return_value = ReleaseTarget(
            COMPONENT, RELEASE_TAG, lock, PLATFORM, "3" * 64, RECIPE
        )
        api = github.return_value
        api.tag_commit.return_value = RECIPE
        notes = f"Publication record for {COMPONENT} {lock.tag} at recipe commit {RECIPE}."
        api.api.return_value = [
            [
                {
                    "tag_name": RELEASE_TAG,
                    "body": notes,
                    "draft": False,
                    "assets": [{"id": 7, "name": "release-record.json"}],
                }
            ]
        ]
        record = {
            "component": COMPONENT,
            "upstream_repository": lock.repository,
            "upstream_tag": lock.tag,
            "upstream_commit": lock.commit,
            "recipe_commit": RECIPE,
            "digest": DIGEST,
            "image": f"{DESTINATION}:{lock.tag}",
            "verified_at": "now",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release-record.json"
            path.write_text(json.dumps(record))
            gh.return_value = json.dumps(record | {"verified_at": "previous"}).encode()
            attach(CONTEXT | {"GH_TOKEN": "mock"}, path)
            gh.assert_called_once()
            self.assertEqual(gh.call_args.args[1][0], "api")
            gh.return_value = json.dumps(record | {"digest": "sha256:" + "4" * 64}).encode()
            with self.assertRaisesRegex(Error, "different image"):
                attach(CONTEXT | {"GH_TOKEN": "mock"}, path)
            gh.reset_mock()
            path.write_text(json.dumps(record | {"image": f"{SOURCE}:{lock.tag}"}))
            with self.assertRaisesRegex(Error, "does not match"):
                attach(CONTEXT | {"GH_TOKEN": "mock"}, path)
            gh.assert_not_called()

    @patch("record_release.run_gh")
    @patch("record_release.GitHub")
    @patch("record_release.preflight")
    def test_retry_replaces_only_empty_draft_asset_placeholder(self, preflight, github, gh):
        lock = load_local(ROOT, COMPONENT)
        preflight.return_value = ReleaseTarget(
            COMPONENT, RELEASE_TAG, lock, PLATFORM, "3" * 64, RECIPE
        )
        api = github.return_value
        api.tag_commit.return_value = RECIPE
        draft = {
            "id": 12,
            "tag_name": RELEASE_TAG,
            "target_commitish": RECIPE,
            "body": f"Publication record for {COMPONENT} {lock.tag} at recipe commit {RECIPE}.",
            "draft": True,
        }
        asset = {"name": "release-record.json", "id": 7}
        api.api.side_effect = [
            [[draft | {"assets": [asset | {"state": "starter", "size": 0}]}]],
            [[draft | {"assets": [asset | {"id": 8, "state": "uploaded"}]}]],
        ]
        record = {
            "component": COMPONENT,
            "upstream_repository": lock.repository,
            "upstream_tag": lock.tag,
            "upstream_commit": lock.commit,
            "recipe_commit": RECIPE,
            "digest": DIGEST,
            "image": f"{DESTINATION}:{lock.tag}",
        }
        gh.side_effect = [b"", b"", json.dumps(record).encode(), b""]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release-record.json"
            path.write_text(json.dumps(record))
            attach(CONTEXT | {"GH_TOKEN": "mock"}, path)
        deleted, uploaded, verified, published = [call.args[1] for call in gh.call_args_list]
        self.assertEqual(
            deleted, ["api", "--method", "DELETE", f"repos/{REPOSITORY}/releases/assets/7"]
        )
        self.assertEqual(uploaded[:2], ["release", "upload"])
        self.assertEqual(verified[1], f"repos/{REPOSITORY}/releases/assets/8")
        self.assertIn("--draft=false", published)

    @patch("record_release.run_gh")
    @patch("record_release.GitHub")
    @patch("record_release.preflight")
    def test_release_record_uses_existing_tag_and_never_creates_one(self, preflight, github, gh):
        lock = load_local(ROOT, COMPONENT)
        preflight.return_value = ReleaseTarget(
            COMPONENT, RELEASE_TAG, lock, PLATFORM, "3" * 64, RECIPE
        )
        api = github.return_value
        api.tag_commit.return_value = RECIPE
        draft = {"id": 12, "tag_name": RELEASE_TAG, "draft": True, "assets": []}
        asset = {"name": "release-record.json", "id": 7}
        api.api.side_effect = [[[]], [[draft]], [[draft | {"assets": [asset]}]]]
        record = {
            "component": COMPONENT,
            "upstream_repository": lock.repository,
            "upstream_tag": lock.tag,
            "upstream_commit": lock.commit,
            "recipe_commit": RECIPE,
            "digest": DIGEST,
            "image": f"{DESTINATION}:{lock.tag}",
        }
        gh.side_effect = [b"", b"", json.dumps(record).encode(), b""]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release-record.json"
            path.write_text(json.dumps(record))
            attach(CONTEXT | {"GH_TOKEN": "mock"}, path)
        create = gh.call_args_list[0].args[1]
        self.assertEqual(create[:3], ["release", "create", RELEASE_TAG])
        self.assertIn("--verify-tag", create)
        self.assertNotIn("--target", create)


class RecipeTests(unittest.TestCase):
    def test_public_check_uses_only_a_temporary_public_context(self):
        recipe = (ROOT / lock_path(COMPONENT)).parent
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            docker = scratch / "docker"
            docker.write_text(
                "#!/bin/bash\n"
                "set -eu\n"
                '[[ "$*" == "buildx build --check --platform linux/amd64 --file "* ]]\n'
                '[[ "$7" == */device-plugin/Dockerfile ]]\n'
                'test -f "$8/source/pkg/cndev/include/.keep"\n'
                'test -f "$8/licenses/.keep"\n'
                "printf '%s\\n' \"$8\"\n"
            )
            docker.chmod(0o755)
            context = subprocess.check_output(
                ["bash", str(recipe / "build.sh"), "--check-public"],
                env={
                    "PATH": f"{scratch}{os.pathsep}{os.environ['PATH']}",
                    "RUNNER_TEMP": directory,
                },
                text=True,
            ).strip()
            self.assertEqual(Path(context).parent.resolve(), scratch.resolve())
            self.assertFalse(Path(context).exists())

    def test_reports_missing_inputs_without_opening_the_build(self):
        recipe = ROOT / lock_path(COMPONENT)
        result = subprocess.run(
            [str(recipe.with_name("build.sh")), "--check-inputs"],
            env={"PATH": os.environ["PATH"]},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        for name in ["CAMBRICON_CNDEV_HEADER", "CAMBRICON_LIBCNDEV", "CAMBRICON_LIBCNTOPO"]:
            self.assertIn(name, result.stderr)

    def test_only_external_amd64_inputs_pass_and_public_ci_cannot_build(self):
        recipe = ROOT / lock_path(COMPONENT)
        path = recipe.with_name("build.sh")
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            header, cndev, cntopo = (
                scratch / name for name in ["cndev.h", "libcndev.so", "libcntopo.so"]
            )
            header.write_text("/* synthetic test input */")
            elf = b"\x7fELF\x02\x01\x01" + b"\0" * 9 + b"\x03\x00\x3e\x00"
            cndev.write_bytes(elf)
            cntopo.write_bytes(elf)
            env = {
                "PATH": os.environ["PATH"],
                "CAMBRICON_CNDEV_HEADER": str(header),
                "CAMBRICON_LIBCNDEV": str(cndev),
                "CAMBRICON_LIBCNTOPO": str(cntopo),
            }
            subprocess.run([str(path), "--check-inputs"], env=env, check=True, capture_output=True)
            refused = subprocess.run(
                [str(path)],
                env=env
                | {
                    "GITHUB_ACTIONS": "true",
                    "CAMBRICON_AUTHORIZED_BUILD": "1",
                },
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertIn("requires an authorized environment", refused.stderr)
            self.assertNotEqual(refused.returncode, 0)
            cntopo.write_bytes(elf[:-2] + b"\xb7\x00")
            with_bad_lib = subprocess.run(
                [str(path), "--check-inputs"], env=env, text=True, capture_output=True, check=False
            )
            self.assertNotEqual(with_bad_lib.returncode, 0)
            self.assertIn("x86-64 ELF shared object", with_bad_lib.stderr)
