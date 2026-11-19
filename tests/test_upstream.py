import argparse
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from github import GitHub
from metadata import (
    REPOSITORY,
    ROOT,
    Error,
    Lock,
    components,
    load_local,
    lock_path,
    parse_lock,
    update_lock,
)
from upstream import Bot, choose_candidate, publish_candidate, require_writer, run

COMPONENT = "cambricon/device-plugin"
PATH = lock_path(COMPONENT)
OLD = Lock("https://github.com/example/plugin", "v2.5.0", "a" * 40)
NEW = replace(OLD, tag="v2.10.0", commit="b" * 40)
BASE = "c" * 40
HEAD = "d" * 40
BRANCH = f"upstream/{COMPONENT}/{NEW.tag}"
BOT = Bot("update-app[bot]", 1234)
SOURCE = f"repository: \"{OLD.repository}\"\ntag: {OLD.tag} # reviewed\ncommit: '{OLD.commit}'\n"


def formal(tag, **overrides):
    return {"tag_name": tag, "draft": False, "prerelease": False, **overrides}


def pull(head, state):
    return {"head": {"ref": head}, "state": state}


class FakeGitHub:
    def __init__(self):
        self.tags = {OLD.tag: OLD.commit, NEW.tag: NEW.commit}
        self.history = []
        self.upstream_releases = [formal(NEW.tag)]
        self.main_sha = BASE
        self.files = {BASE: SOURCE}
        self.branches = {}
        self.commits = {}
        self.writes = []
        self.pr_outcome = None
        self.commit_response_lost = False

    def main(self):
        return self.main_sha

    def releases(self, slug):
        return self.upstream_releases

    def tag_commit(self, slug, tag):
        return self.tags.get(tag)

    def pr_history(self):
        return self.history

    def head(self, branch):
        return self.branches.get(branch)

    def file_at(self, path, commit):
        assert path == PATH
        return self.files[commit]

    def is_ancestor(self, ancestor, descendant):
        return ancestor == descendant or (ancestor == BASE and descendant == self.main_sha)

    def create_ref(self, branch, base):
        self.writes.append("branch")
        self.branches[branch] = base

    def create_commit(self, branch, parent, path, content, title, bot):
        assert self.branches[branch] == parent
        self.writes.append("commit")
        self.branches[branch] = HEAD
        self.files[HEAD] = content
        self.commits[HEAD] = {
            "sha": HEAD,
            "author": {"login": bot.login},
            "commit": {
                "message": f"{title}\n\n{bot.signoff}",
                "author": {"email": bot.email},
                "verification": {"verified": True, "reason": "valid"},
            },
            "files": [{"filename": path, "status": "modified"}],
            "parents": [{"sha": parent}],
        }
        if self.commit_response_lost:
            raise subprocess.TimeoutExpired("gh", 1)
        return HEAD

    def commit(self, sha):
        return self.commits[sha]

    def create_pr(self, branch, title, body):
        self.writes.append("pr")
        self.body = body
        if self.pr_outcome == "unavailable":
            raise Error("create update PR failed")
        if self.pr_outcome == "other-branch":
            self.history.append(pull(f"upstream/{COMPONENT}/v2.9.9", "open"))
            raise Error("create update PR failed")
        self.history.append(pull(branch, "open"))
        if self.pr_outcome == "response-lost":
            raise Error("create update PR failed")


class MetadataTests(unittest.TestCase):
    def test_schema_preserves_comments_when_advancing(self):
        self.assertEqual(parse_lock(SOURCE), OLD)
        result = update_lock(SOURCE, NEW)
        self.assertIn('tag: "v2.10.0" # reviewed', result)
        self.assertEqual(parse_lock(result), NEW)

    def test_rejects_invalid_schema_values(self):
        for invalid in [
            SOURCE + "tag: v3.0.0\n",
            SOURCE + "extra: value\n",
            SOURCE.replace("# reviewed", "# comment").replace("v2.5.0", "v2.5.0-rc.1"),
            SOURCE.replace("github.com", "git.example.com"),
            SOURCE.split("commit:")[0],
            SOURCE.replace(f"'{OLD.commit}'", "1" * 40),
        ]:
            with self.subTest(invalid=invalid), self.assertRaises(Error):
                parse_lock(invalid)

    @patch("upstream.check_base")
    def test_automated_ci_check_targets_only_its_component(self, check):
        lock = load_local(ROOT, COMPONENT)
        args = argparse.Namespace(
            command="check",
            base=BASE,
            automatic_head=f"upstream/{COMPONENT}/{lock.tag}",
            offline=True,
        )
        self.assertEqual(run(args, {}), 0)
        by_component = {call.args[1]: call.args[4] for call in check.call_args_list}
        self.assertEqual(
            by_component,
            {
                component: args.automatic_head if component == COMPONENT else None
                for component in components(ROOT)
            },
        )

    @patch("upstream.GitHub")
    def test_moved_lock_on_one_component_does_not_skip_others(self, github):
        locks = [
            load_local(ROOT, component) for component in components(ROOT) if component != COMPONENT
        ]
        tags = {(lock.slug, lock.tag): lock.commit for lock in locks}
        github.return_value.tag_commit.side_effect = lambda slug, tag: tags.get((slug, tag))
        args = argparse.Namespace(command="check", base=None, automatic_head=None, offline=False)
        self.assertEqual(run(args, {}), 1)
        self.assertEqual(github.return_value.tag_commit.call_count, len(locks) + 1)


class ProtocolTests(unittest.TestCase):
    @patch.object(GitHub, "api")
    def test_annotated_tag_is_peeled_through_nested_tags(self, api):
        api.side_effect = [
            {"object": {"type": "tag", "sha": "e" * 40}},
            {"object": {"type": "tag", "sha": "f" * 40}},
            {"object": {"type": "commit", "sha": OLD.commit}},
        ]
        self.assertEqual(GitHub().tag_commit(OLD.slug, OLD.tag), OLD.commit)
        self.assertEqual(api.call_count, 3)

    @patch("github.run_gh")
    def test_releases_include_all_pages_using_read_token(self, gh):
        gh.return_value = b'[[{"tag_name":"v2.9.0"}],[{"tag_name":"v2.10.0"}]]'
        self.assertEqual(len(GitHub("read", "write").releases(OLD.slug)), 2)
        self.assertEqual(gh.call_args.args[0], "read")
        self.assertIn("--paginate", gh.call_args.args[1])

    @patch("github.run_gh")
    def test_mutation_uses_app_token_single_file_and_compare_and_swap(self, gh):
        import base64
        import json

        gh.return_value = b'{"data":{"createCommitOnBranch":{"commit":{"oid":"commit"}}}}'
        GitHub("read", "write").create_commit(BRANCH, BASE, PATH, SOURCE, "title", BOT)
        token, args, _, raw = gh.call_args.args
        self.assertEqual(token, "write")
        self.assertIn("graphql", args)
        changes = json.loads(raw)["variables"]["input"]
        self.assertEqual(changes["expectedHeadOid"], BASE)
        self.assertEqual(changes["branch"]["branchName"], BRANCH)
        self.assertEqual(changes["message"]["body"], BOT.signoff)
        additions = changes["fileChanges"]["additions"]
        self.assertEqual(
            additions, [{"path": PATH, "contents": base64.b64encode(SOURCE.encode()).decode()}]
        )

    @patch("github.run_gh")
    def test_pr_submission_uses_body_file_and_fixed_repository(self, gh):
        def check(token, args, operation):
            self.assertEqual(token, "write")
            self.assertEqual(args[args.index("--repo") + 1], REPOSITORY)
            self.assertEqual(args[args.index("--head") + 1], BRANCH)
            self.assertEqual(args[args.index("--base") + 1], "main")
            self.assertEqual(Path(args[args.index("--body-file") + 1]).read_text(), "PR body")

        gh.side_effect = check
        GitHub("read", "write").create_pr(BRANCH, "title", "PR body")
        gh.assert_called_once()


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeGitHub()

    def publish(self):
        return publish_candidate(self.api, COMPONENT, SOURCE, NEW, BOT)

    def test_writer_refuses_forks_disabled_unverified_or_builtin_token(self):
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": REPOSITORY,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "schedule",
            "GITHUB_WORKFLOW_REF": f"{REPOSITORY}/.github/workflows/upstream.yml@refs/heads/main",
            "UPSTREAM_WRITE_ENABLED": "true",
            "UPSTREAM_SIGNING_DCO_VERIFIED": "true",
            "UPSTREAM_APP_TOKEN": "write",
            "GH_TOKEN": "read",
            "UPSTREAM_APP_SLUG": "update-app",
        }
        self.assertEqual(require_writer(env), ("write", "update-app[bot]"))
        for name, value in {
            "GITHUB_REPOSITORY": "fork/accelerator-artifacts",
            "GITHUB_REF": "refs/heads/feature",
            "GITHUB_EVENT_NAME": "pull_request",
            "UPSTREAM_WRITE_ENABLED": "false",
            "UPSTREAM_SIGNING_DCO_VERIFIED": "",
            "UPSTREAM_APP_TOKEN": "read",
            "GITHUB_WORKFLOW_REF": "unreviewed-workflow",
        }.items():
            with self.subTest(setting=name), self.assertRaises(Error):
                require_writer(env | {name: value})

    def test_selects_numerically_highest_formal_unhandled_version(self):
        self.api.upstream_releases += [
            formal("v2.6.0"),
            formal("v2.9.0"),
            formal("v3.1.0", draft=True),
            formal("v3.2.0", prerelease=True),
            formal("v3.3.0-rc.1"),
        ]
        self.assertEqual(choose_candidate(self.api, COMPONENT, OLD, []), NEW)
        self.api.tags["v2.9.0"] = "e" * 40
        self.assertEqual(
            choose_candidate(self.api, COMPONENT, OLD, [pull(BRANCH, "closed")]).tag, "v2.9.0"
        )
        self.assertIsNone(choose_candidate(self.api, COMPONENT, OLD, [pull(BRANCH, "open")]))

    def test_normal_creation_is_narrow_and_rerun_preserves_open_pr(self):
        self.assertEqual(self.publish(), "opened update PR")
        self.assertEqual(self.api.writes, ["branch", "commit", "pr"])
        self.assertEqual(parse_lock(self.api.files[HEAD]), NEW)
        self.assertEqual(self.publish(), "preserved existing PR")
        self.assertEqual(self.api.writes, ["branch", "commit", "pr"])
        for value in [PATH, OLD.tag, NEW.tag, OLD.commit, NEW.commit, "/compare/", "libcntopo.so"]:
            self.assertIn(value, self.api.body)

    def test_retry_recovers_branch_created_without_commit(self):
        self.api.branches[BRANCH] = BASE
        self.assertEqual(self.publish(), "opened update PR")
        self.assertEqual(self.api.writes, ["commit", "pr"])

    def test_retry_after_pr_failure_resumes_the_signed_branch(self):
        self.api.pr_outcome = "unavailable"
        with self.assertRaises(Error):
            self.publish()
        self.api.pr_outcome = None
        self.assertEqual(self.publish(), "opened update PR")
        self.assertEqual(self.api.writes, ["branch", "commit", "pr", "pr"])

    def test_recovers_lost_commit_response_and_exact_head_pr_conflict(self):
        self.api.commit_response_lost = True
        self.api.pr_outcome = "response-lost"
        self.assertEqual(self.publish(), "found existing exact-head PR after create failure")
        self.assertEqual(self.api.writes, ["branch", "commit", "pr"])

    def test_other_pr_does_not_convert_create_failure_into_success(self):
        self.api.pr_outcome = "other-branch"
        with self.assertRaisesRegex(Error, "create update PR failed"):
            self.publish()

    def test_stale_main_and_moved_candidate_fail_before_writes(self):
        self.api.files[BASE] = update_lock(SOURCE, NEW)
        with self.assertRaisesRegex(Error, "stale"):
            self.publish()
        self.api.files[BASE] = SOURCE
        self.api.tags[NEW.tag] = "f" * 40
        with self.assertRaisesRegex(Error, "locked at"):
            self.publish()
        self.assertEqual(self.api.writes, [])

    def test_preserves_branch_with_review_changes_or_unsigned_commit(self):
        self.api.pr_outcome = "unavailable"
        with self.assertRaises(Error):
            self.publish()
        self.api.commits[HEAD]["files"].append({"filename": "README.md", "status": "modified"})
        self.api.commits[HEAD]["commit"]["verification"]["verified"] = False
        self.api.writes.clear()
        with self.assertRaisesRegex(Error, "does not match"):
            self.publish()
        self.assertEqual(self.api.writes, [])
