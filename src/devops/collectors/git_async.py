"""Async-compatible Git collector for use with Textual workers."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from devops.cache.git_cache import load_cached_repos
from devops.collectors.base import EnvEntry, Status


@dataclass
class GitCollectResult:
    """Result from collecting git data."""

    entries: list[EnvEntry]
    repo_count: int


def _run_git(repo_path: str, args: list[str]) -> str:
    """Run a git command in the given repository."""
    result = subprocess.run(
        ["git"] + args,
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout


def _get_repo_status(path: str) -> EnvEntry | None:
    """Get status for a single repository."""
    repo_path = Path(path)

    # Check if repo still exists
    if not (repo_path / ".git").exists():
        return EnvEntry(
            name=repo_path.name,
            path=str(repo_path),
            status=Status.ERROR,
            details={
                "error": "Repository not found",
                "branch": "?",
                "clean": False,
            },
        )

    try:
        # Get current branch
        branch = _run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()

        # Get status
        status_output = _run_git(path, ["status", "--porcelain", "-b"])
        lines = status_output.strip().split("\n") if status_output.strip() else []

        # Parse branch line for ahead/behind
        ahead = 0
        behind = 0
        if lines and lines[0].startswith("##"):
            branch_line = lines[0]
            if "[" in branch_line:
                tracking_info = branch_line.split("[")[1].rstrip("]")
                if "ahead" in tracking_info:
                    ahead = int(
                        tracking_info.split("ahead ")[1].split(",")[0].split("]")[0]
                    )
                if "behind" in tracking_info:
                    behind = int(
                        tracking_info.split("behind ")[1].split(",")[0].split("]")[0]
                    )

        # Count file statuses
        modified = 0
        staged = 0
        untracked = 0

        for line in lines[1:]:  # Skip branch line
            if not line:
                continue
            index_status = line[0] if len(line) > 0 else " "
            worktree_status = line[1] if len(line) > 1 else " "

            if index_status == "?":
                untracked += 1
            else:
                if index_status not in " ?":
                    staged += 1
                if worktree_status not in " ?":
                    modified += 1

        # Get remote URL
        remote_url = ""
        try:
            remote_url = _run_git(path, ["remote", "get-url", "origin"]).strip()
        except Exception:
            pass

        # Get last commit info
        last_commit = ""
        last_commit_msg = ""
        last_commit_date = ""
        try:
            log_output = _run_git(path, ["log", "-1", "--format=%h|%s|%cr"]).strip()
            if "|" in log_output:
                parts = log_output.split("|", 2)
                last_commit = parts[0]
                last_commit_msg = parts[1] if len(parts) > 1 else ""
                last_commit_date = parts[2] if len(parts) > 2 else ""
        except Exception:
            pass

        # Determine overall status
        is_clean = modified == 0 and staged == 0 and untracked == 0

        if branch == "HEAD":
            # Detached HEAD
            status = Status.ERROR
        elif not is_clean:
            status = Status.WARNING
        elif ahead > 0 or behind > 0:
            status = Status.WARNING
        else:
            status = Status.HEALTHY

        return EnvEntry(
            name=repo_path.name,
            path=str(repo_path),
            status=status,
            details={
                "branch": branch,
                "clean": is_clean,
                "ahead": ahead,
                "behind": behind,
                "modified": modified,
                "staged": staged,
                "untracked": untracked,
                "remote_url": remote_url,
                "last_commit": last_commit,
                "last_commit_msg": last_commit_msg,
                "last_commit_date": last_commit_date,
            },
        )

    except Exception as e:
        return EnvEntry(
            name=repo_path.name,
            path=str(repo_path),
            status=Status.ERROR,
            details={
                "error": str(e),
                "branch": "?",
                "clean": False,
            },
        )


def collect_git_sync() -> GitCollectResult:
    """Collect all git repository data synchronously.

    This is designed to be called from a Textual thread worker.
    """
    repos = load_cached_repos()

    if not repos:
        return GitCollectResult(entries=[], repo_count=0)

    entries = []
    for repo_path in repos:
        entry = _get_repo_status(repo_path)
        if entry:
            entries.append(entry)

    return GitCollectResult(entries=entries, repo_count=len(repos))
