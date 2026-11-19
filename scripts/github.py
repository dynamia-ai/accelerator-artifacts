"""GitHub queries and release commands used by the repository workflows."""

import base64
import json
import os
import subprocess

from metadata import REPOSITORY, SHA, Error


class GitHubError(Error):
    def __init__(self, operation, result):
        super().__init__(f"{operation} failed")
        self.not_found = b"HTTP 404" in result.stderr or (
            b"HTTP 409" in result.stderr and b"Git Repository is empty" in result.stderr
        )


def run_gh(token, args, operation):
    env = {**os.environ, "GH_HOST": "github.com", "GH_PROMPT_DISABLED": "1"}
    env.pop("GH_DEBUG", None)
    if token:
        env["GH_TOKEN"] = token
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        env=env,
        timeout=120,
        check=False,
    )
    if result.returncode:
        raise GitHubError(operation, result)
    return result.stdout


class GitHub:
    def __init__(self, token=None):
        self.token = token

    def api(self, route, *, operation, pages=False):
        args = ["api", route]
        if pages:
            args += ["--paginate", "--slurp"]
        return json.loads(run_gh(self.token, args, operation))

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

    def release(self, slug, tag):
        try:
            return self.api(
                f"repos/{slug}/releases/tags/{tag}", operation="read published upstream release"
            )
        except GitHubError as error:
            if error.not_found:
                return None
            raise

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

    def is_ancestor(self, ancestor, descendant):
        if ancestor == descendant:
            return True
        comparison = self.api(
            f"repos/{REPOSITORY}/compare/{ancestor}...{descendant}",
            operation="check commit ancestry",
        )
        return comparison["status"] in {"ahead", "identical"}
