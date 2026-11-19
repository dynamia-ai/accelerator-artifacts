"""GitHub operations for public reads and the separately gated App writer."""

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

from metadata import REPOSITORY, SHA, Error


class GitHubError(Error):
    def __init__(self, operation, result):
        super().__init__(f"{operation} failed")
        self.not_found = b"HTTP 404" in result.stderr or (
            b"HTTP 409" in result.stderr and b"Git Repository is empty" in result.stderr
        )
        self.conflict = b"HTTP 422" in result.stderr or b"HTTP 409" in result.stderr


def run_gh(token, args, operation, payload=None):
    env = {**os.environ, "GH_HOST": "github.com", "GH_PROMPT_DISABLED": "1"}
    env.pop("GH_DEBUG", None)
    env.pop("UPSTREAM_APP_TOKEN", None)
    if token:
        env["GH_TOKEN"] = token
    result = subprocess.run(
        ["gh", *args],
        input=payload,
        capture_output=True,
        env=env,
        timeout=120,
        check=False,
    )
    if result.returncode:
        raise GitHubError(operation, result)
    return result.stdout


class GitHub:
    def __init__(self, read_token=None, app_token=None):
        self.read_token = read_token
        self.app_token = app_token

    def api(self, route, *, operation, pages=False, payload=None, app=False):
        args = ["api", route]
        if pages:
            args += ["--paginate", "--slurp"]
        data = None
        if payload is not None:
            args += ["--method", "POST", "--input", "-"]
            data = json.dumps(payload).encode()
        token = self.app_token if app else self.read_token
        if app and not token:
            raise Error("App token is required for writes")
        return json.loads(run_gh(token, args, operation, data))

    def tag_commit(self, slug, tag):
        ref = self.ref(slug, "tags", tag)
        if ref is None:
            return None
        obj = ref["object"]
        seen = set()
        while obj["type"] == "tag":
            sha = obj["sha"]
            if not SHA.fullmatch(sha) or sha in seen or len(seen) == 16:
                raise Error(f"invalid annotated tag chain for {slug} {tag}")
            seen.add(sha)
            obj = self.api(f"repos/{slug}/git/tags/{sha}", operation="resolve annotated tag")[
                "object"
            ]
        if obj["type"] != "commit" or not SHA.fullmatch(obj["sha"]):
            raise Error(f"tag does not resolve to a commit for {slug} {tag}")
        return obj["sha"]

    def ref(self, slug, namespace, name):
        try:
            return self.api(
                f"repos/{slug}/git/ref/{namespace}/{name}", operation=f"read {namespace} ref"
            )
        except GitHubError as error:
            if error.not_found:
                return None
            raise

    def releases(self, slug):
        pages = self.api(
            f"repos/{slug}/releases?per_page=100", pages=True, operation="list upstream releases"
        )
        return [release for page in pages for release in page]

    def pr_history(self):
        # Query under the same GitHub App when writing so it can also see draft PRs.
        pages = self.api(
            f"repos/{REPOSITORY}/pulls?state=all&base=main&per_page=100",
            pages=True,
            operation="read PR history",
            app=bool(self.app_token),
        )
        return [
            pull
            for page in pages
            for pull in page
            if pull["base"]["ref"] == "main"
            and pull["head"].get("repo")
            and pull["head"]["repo"]["full_name"].lower() == REPOSITORY.lower()
        ]

    def head(self, branch):
        ref = self.ref(REPOSITORY, "heads", branch)
        if ref is None:
            return None
        if ref["object"]["type"] != "commit" or not SHA.fullmatch(ref["object"]["sha"]):
            raise Error("branch does not resolve to a commit")
        return ref["object"]["sha"]

    def main(self):
        head = self.head("main")
        if head is None:
            raise Error("main baseline is missing")
        return head

    def file_at(self, path, commit):
        data = self.api(
            f"repos/{REPOSITORY}/contents/{path}?ref={commit}",
            operation="read reviewed file from GitHub",
        )
        if data.get("type") != "file" or data.get("encoding") != "base64":
            raise Error("reviewed GitHub file is not a regular file")
        return base64.b64decode(data["content"]).decode()

    def create_ref(self, branch, base):
        try:
            self.api(
                f"repos/{REPOSITORY}/git/refs",
                operation="create update branch",
                app=True,
                payload={"ref": f"refs/heads/{branch}", "sha": base},
            )
        except GitHubError as error:
            if not error.conflict or self.head(branch) is None:
                raise

    def create_commit(self, branch, parent, path, content, title, bot):
        query = """
        mutation($input: CreateCommitOnBranchInput!) {
          createCommitOnBranch(input: $input) { commit { oid } }
        }
        """
        result = self.api(
            "graphql",
            operation="create GitHub-signed commit",
            app=True,
            payload={
                "query": query,
                "variables": {
                    "input": {
                        "branch": {"repositoryNameWithOwner": REPOSITORY, "branchName": branch},
                        "expectedHeadOid": parent,
                        "message": {"headline": title, "body": bot.signoff},
                        "fileChanges": {
                            "additions": [
                                {
                                    "path": path,
                                    "contents": base64.b64encode(content.encode()).decode("ascii"),
                                }
                            ]
                        },
                    }
                },
            },
        )
        return result["data"]["createCommitOnBranch"]["commit"]["oid"]

    def commit(self, sha):
        return self.api(
            f"repos/{REPOSITORY}/commits/{sha}", operation="inspect branch commit", app=True
        )

    def is_ancestor(self, ancestor, descendant):
        if ancestor == descendant:
            return True
        comparison = self.api(
            f"repos/{REPOSITORY}/compare/{ancestor}...{descendant}",
            operation="check update branch ancestry",
        )
        return comparison["status"] in {"ahead", "identical"}

    def bot_id(self, login):
        user = self.api(f"users/{quote(login, safe='')}", operation="resolve App bot account")
        if user["login"] != login or user["type"] != "Bot" or not isinstance(user["id"], int):
            raise Error("GitHub App bot identity could not be confirmed")
        return user["id"]

    def create_pr(self, branch, title, body):
        if not self.app_token:
            raise Error("App token is required to create a PR")
        with tempfile.TemporaryDirectory(prefix="upstream-pr-") as scratch:
            body_file = Path(scratch) / "body.md"
            body_file.write_text(body, encoding="utf-8")
            run_gh(
                self.app_token,
                [
                    "pr",
                    "create",
                    "--repo",
                    REPOSITORY,
                    "--base",
                    "main",
                    "--head",
                    branch,
                    "--title",
                    title,
                    "--body-file",
                    str(body_file),
                ],
                "create update PR",
            )
