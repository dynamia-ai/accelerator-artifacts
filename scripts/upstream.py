"""Check reviewed upstream locks and propose narrowly scoped Release upgrades."""

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass

from github import GitHub
from metadata import (
    COMPONENT,
    REPOSITORY,
    ROOT,
    SHA,
    TAG,
    Error,
    Lock,
    check_base,
    components,
    load_local,
    lock_path,
    parse_lock,
    update_lock,
    version,
)


@dataclass(frozen=True)
class Bot:
    login: str
    user_id: int

    @property
    def signoff(self):
        return f"Signed-off-by: {self.login} <{self.email}>"

    @property
    def email(self):
        return f"{self.user_id}+{self.login}@users.noreply.github.com"


def require_writer(env):
    if (
        env.get("GITHUB_ACTIONS") != "true"
        or env.get("GITHUB_REPOSITORY") != REPOSITORY
        or env.get("GITHUB_REF") != "refs/heads/main"
        or env.get("GITHUB_WORKFLOW_REF")
        != f"{REPOSITORY}/.github/workflows/upstream.yml@refs/heads/main"
        or env.get("GITHUB_EVENT_NAME") not in {"schedule", "workflow_dispatch"}
        or env.get("UPSTREAM_WRITE_ENABLED") != "true"
        or env.get("UPSTREAM_SIGNING_DCO_VERIFIED") != "true"
    ):
        raise Error(
            "writes require the enabled upstream workflow on original main and verified signing/DCO"
        )
    app_token = env.get("UPSTREAM_APP_TOKEN")
    read_token = env.get("GH_TOKEN")
    slug = env.get("UPSTREAM_APP_SLUG", "")
    if (
        not read_token
        or not app_token
        or app_token == read_token
        or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug)
    ):
        raise Error("writes require a distinct App token and its bot identity")
    return app_token, f"{slug}[bot]"


def branch_prefix(component):
    lock_path(component)
    return f"upstream/{component}/"


def matching_prs(history, component):
    prefix = branch_prefix(component)
    return [pull for pull in history if pull["head"]["ref"].startswith(prefix)]


def verify_lock(api, lock):
    actual = api.tag_commit(lock.slug, lock.tag)
    if actual != lock.commit:
        raise Error(
            f"{lock.slug} {lock.tag} locked at {lock.commit}; upstream is {actual or 'missing'}"
        )


def official_tags(api, lock):
    return {
        release["tag_name"]
        for release in api.releases(lock.slug)
        if not release["draft"] and not release["prerelease"] and TAG.fullmatch(release["tag_name"])
    }


def choose_candidate(api, component, current, history):
    verify_lock(api, current)
    existing = matching_prs(history, component)
    if any(pull["state"] == "open" for pull in existing):
        return None
    handled = {pull["head"]["ref"] for pull in existing}
    prefix = branch_prefix(component)
    tags = [
        tag
        for tag in official_tags(api, current)
        if version(tag) > current.version and prefix + tag not in handled
    ]
    if not tags:
        return None
    tag = max(tags, key=version)
    sha = api.tag_commit(current.slug, tag)
    if sha is None:
        raise Error(f"release {tag} has no upstream tag")
    return Lock(current.repository, tag, sha)


def pr_body(component, current, candidate):
    cambricon = component == "cambricon/device-plugin"
    review = [
        "- [ ] Review upstream changes, licensing, and any recipe changes.",
        "- [ ] Check version-specific licensing coverage for any planned public image.",
    ]
    if cambricon:
        review += [
            "- [ ] Confirm header and runtime library versions and check an authorized linux/amd64 build.",
            "- [ ] Confirm authorization to redistribute libcndev.so and libcntopo.so in the public image.",
        ]
    return "\n".join(
        [
            "## Upstream update",
            "",
            f"- Lock file: `{lock_path(component)}`",
            f"- Previous: `{current.tag}` at `{current.commit}`",
            f"- Candidate: `{candidate.tag}` at `{candidate.commit}`",
            f"- [Upstream Release]({candidate.repository}/releases/tag/{candidate.tag})",
            f"- [Source comparison]({candidate.repository}/compare/{current.commit}...{candidate.commit})",
            "",
            "## Checks",
            "",
            "- Verified the current and candidate tag commit SHAs and the candidate's formal Release.",
            "- Verified that the update branch changes only the selected lock file and that the App commit is signed.",
            "",
            "## Review before merge",
            "",
            *review,
            "",
        ]
    )


def verify_update_commit(api, head, path, expected_source, bot, title):
    detail = api.commit(head)
    commit = detail["commit"]
    signature = commit["verification"]
    parent = detail["parents"]
    files = [(item["filename"], item["status"]) for item in detail["files"]]
    message = f"{title}\n\n{bot.signoff}"
    if (
        detail["sha"] != head
        or not signature["verified"]
        or signature["reason"] != "valid"
        or (detail.get("author") or {}).get("login") != bot.login
        or commit["author"]["email"] != bot.email
        or commit["message"].rstrip("\n") != message
        or len(parent) != 1
        or files != [(path, "modified")]
        or api.file_at(path, head) != expected_source
    ):
        raise Error("update branch commit does not match the signed single-file update")
    return parent[0]["sha"]


def refresh_base(api, path, expected_source, candidate):
    main = api.main()
    if api.file_at(path, main) != expected_source:
        raise Error("candidate is stale because the lock on main changed")
    verify_lock(api, parse_lock(expected_source))
    verify_lock(api, candidate)
    if candidate.tag not in official_tags(api, candidate):
        raise Error("candidate is no longer a formal Release")
    return main


def publish_candidate(api, component, expected_source, candidate, bot):
    path = lock_path(component)
    current = parse_lock(expected_source)
    updated = update_lock(expected_source, candidate)
    branch = branch_prefix(component) + candidate.tag
    title = f"chore({component}): bump upstream to {candidate.tag}"
    existing = matching_prs(api.pr_history(), component)
    if any(p["head"]["ref"] == branch or p["state"] == "open" for p in existing):
        return "preserved existing PR"

    main = refresh_base(api, path, expected_source, candidate)
    head = api.head(branch)
    if head is None:
        api.create_ref(branch, main)
        head = api.head(branch)
        if head is None:
            raise Error("update branch is missing after branch creation")

    # A branch left by an interrupted run can still point to its original base.
    if api.is_ancestor(head, main):
        if api.file_at(path, head) != expected_source:
            raise Error("existing branch points to a stale lock")
        main = refresh_base(api, path, expected_source, candidate)
        if not api.is_ancestor(head, main):
            raise Error("existing branch no longer points into main")
        try:
            created = api.create_commit(branch, head, path, updated, title, bot)
        except Error, subprocess.TimeoutExpired:
            # The request may have succeeded without a response or lost a CAS race.
            created = api.head(branch)
            if created is None or created == head:
                raise
        head = created

    parent = verify_update_commit(api, head, path, updated, bot, title)
    main = refresh_base(api, path, expected_source, candidate)
    if not api.is_ancestor(parent, main) or api.file_at(path, parent) != expected_source:
        raise Error("existing update branch has an unexpected base")
    if api.head(branch) != head:
        raise Error("update branch changed before PR creation")

    existing = matching_prs(api.pr_history(), component)
    if any(p["head"]["ref"] == branch or p["state"] == "open" for p in existing):
        return "preserved existing PR"
    try:
        api.create_pr(branch, title, pr_body(component, current, candidate))
    except Error, subprocess.TimeoutExpired:
        if not any(p["head"]["ref"] == branch for p in api.pr_history()):
            raise
        return "found existing exact-head PR after create failure"
    return "opened update PR"


def run(args, env):
    read_token = env.get("GH_TOKEN")
    if args.command == "poll" and args.write:
        token, login = require_writer(env)
        api = GitHub(read_token, token)
        main = api.main()
        if not SHA.fullmatch(env.get("GITHUB_SHA", "")):
            raise Error("writer requires a checked-out main workflow SHA")
        # A stale workflow might run logic or component configuration since replaced on main.
        if main != env["GITHUB_SHA"]:
            raise Error("workflow main SHA is stale; run the current workflow")
        bot = Bot(login, api.bot_id(login))
    else:
        api = GitHub(read_token)
        bot = None

    automatic_component = None
    if args.command == "check" and args.automatic_head:
        branch = args.automatic_head.split("/")
        if len(branch) != 4 or branch[0] != "upstream":
            raise Error("invalid automatic update head")
        _, vendor, component_name, tag = branch
        automatic_component = f"{vendor}/{component_name}"
        if not COMPONENT.fullmatch(automatic_component) or not TAG.fullmatch(tag):
            raise Error("invalid automatic update head")
        load_local(ROOT, automatic_component)

    failures = 0
    checked = 0
    for component in components(ROOT):
        try:
            current = load_local(ROOT, component)
            if args.command == "check":
                if args.base:
                    automatic_head = (
                        args.automatic_head if component == automatic_component else None
                    )
                    check_base(ROOT, component, current, args.base, automatic_head)
                if not args.offline:
                    verify_lock(api, current)
                print(f"{component}: lock valid ({current.tag})")
            else:
                history = api.pr_history()
                candidate = choose_candidate(api, component, current, history)
                if candidate is None:
                    print(f"{component}: no pending upgrade")
                elif bot:
                    source = api.file_at(lock_path(component), main)
                    if parse_lock(source) != current:
                        raise Error("checkout differs from the original main lock")
                    result = publish_candidate(api, component, source, candidate, bot)
                    print(f"{component}: {candidate.tag}: {result}")
                else:
                    print(f"{component}: {current.tag} -> {candidate.tag} ({candidate.commit})")
            checked += 1
        except (
            Error,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            subprocess.SubprocessError,
        ) as error:
            print(
                f"{component}: {error}"
                if isinstance(error, Error)
                else f"{component}: validation or GitHub operation failed",
                file=sys.stderr,
            )
            failures += 1
    if not checked and not failures:
        raise Error("no component locks found")
    return int(bool(failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check")
    check.add_argument("--offline", action="store_true")
    check.add_argument("--base")
    check.add_argument("--automatic-head")
    poll = commands.add_parser("poll")
    poll.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.command == "check":
        if args.base and not SHA.fullmatch(args.base):
            parser.error("--base must be a full SHA")
        if args.automatic_head and not args.base:
            parser.error("--automatic-head requires --base")
    try:
        return run(args, os.environ)
    except (Error, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(
            str(error) if isinstance(error, Error) else "validation or GitHub operation failed",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
