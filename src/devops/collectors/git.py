"""Git repository collector."""

import os
import subprocess
from pathlib import Path

from devops.cache.git_cache import load_cached_repos

from .base import BaseCollector, EnvEntry, Status

# Directories to skip when scanning for git repos
SKIP_DIRECTORIES = {
    # macOS system directories
    "Applications",
    "Library",
    "System",
    "Users",  # Skip when scanning root, but not when inside home
    "Volumes",
    "cores",
    "private",
    "bin",
    "sbin",
    "usr",
    "var",
    "etc",
    "tmp",
    # macOS app/data directories
    "Music",
    "Movies",
    "Pictures",
    "Photos Library.photoslibrary",
    "Desktop",  # Usually not where repos live
    "Documents",  # Can skip if you want, but some people put repos here
    "Downloads",
    "Public",
    "Creative Cloud Files",
    "Google Drive",
    "Dropbox",
    "OneDrive",
    "iCloud Drive",
    "Parallels",
    "Virtual Machines.localized",
    # Application support / caches
    "Application Support",
    "Caches",
    "Containers",
    "Group Containers",
    "Saved Application State",
    "WebKit",
    "Logs",
    "Preferences",
    "Cookies",
    # Development build/dependency directories
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    "target",
    ".tox",
    ".nox",
    "eggs",
    ".eggs",
    "wheels",
    "sdist",
    "develop-eggs",
    ".installed.cfg",
    "pip-wheel-metadata",
    "share",  # Often virtualenv stuff
    "lib",  # Often virtualenv stuff
    "lib64",
    "include",
    # IDE / editor directories
    ".idea",
    ".vscode",
    ".vs",
    # Other common skips
    "Trash",
    ".Trash",
    "vendor",
    "vendors",
    "bower_components",
    "jspm_packages",
    ".npm",
    ".yarn",
    ".pnpm-store",
    "coverage",
    ".nyc_output",
    "htmlcov",
    ".coverage",
    ".gradle",
    ".m2",
    ".cargo",
    ".rustup",
    "go",  # GOPATH
    ".miniconda",
    ".conda",
    "miniconda3",
    "anaconda3",
    ".pyenv",
    ".rbenv",
    ".nvm",
    ".fnm",
    ".asdf",
    ".local",
    ".cache",
    ".config",
    # Backup directories
    "Backups.backupdb",
    "MobileSync",
}


class GitCollector(BaseCollector):
    """Collector for Git repositories."""

    name = "git"
    description = "Git repositories"

    @staticmethod
    def is_available() -> bool:
        """Check if git is installed (fast filesystem check)."""
        git_paths = [
            "/usr/bin/git",
            "/usr/local/bin/git",
            "/opt/homebrew/bin/git",
        ]
        return any(Path(p).exists() for p in git_paths)

    def collect(self) -> list[EnvEntry]:
        """Collect status for cached repositories."""
        repos = load_cached_repos()

        if not repos:
            # Return empty list - MainScreen will show setup UI
            return []

        entries = []
        for repo_path in repos:
            entry = self._get_repo_status(repo_path)
            if entry:
                entries.append(entry)

        return entries

    def _get_repo_status(self, path: str) -> EnvEntry | None:
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
            branch = self._run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()

            # Get status
            status_output = self._run_git(path, ["status", "--porcelain", "-b"])
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
                            tracking_info.split("behind ")[1]
                            .split(",")[0]
                            .split("]")[0]
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
                remote_url = self._run_git(
                    path, ["remote", "get-url", "origin"]
                ).strip()
            except Exception:
                pass

            # Get last commit info
            last_commit = ""
            last_commit_msg = ""
            last_commit_date = ""
            try:
                log_output = self._run_git(
                    path, ["log", "-1", "--format=%h|%s|%cr"]
                ).strip()
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

    def _run_git(self, repo_path: str, args: list[str]) -> str:
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

    @staticmethod
    def scan_directory(path: str, max_depth: int = 5) -> list[str]:
        """Find all git repositories under a path.

        Args:
            path: Directory to scan
            max_depth: Maximum directory depth to search

        Returns:
            List of repository root paths
        """
        repos = []
        root_path = Path(path).expanduser().resolve()

        if not root_path.exists():
            return repos

        # Check if this path itself is a repo
        if (root_path / ".git").exists():
            repos.append(str(root_path))
            return repos

        # Scan subdirectories
        def scan(dir_path: Path, depth: int):
            if depth > max_depth:
                return

            try:
                for entry in dir_path.iterdir():
                    if not entry.is_dir():
                        continue

                    # Skip hidden directories (except .git which we check)
                    if entry.name.startswith("."):
                        continue

                    # Skip common non-repo directories
                    if entry.name in SKIP_DIRECTORIES:
                        continue

                    # Check if this is a git repo
                    if (entry / ".git").exists():
                        repos.append(str(entry))
                        # Don't recurse into repos (no nested repos)
                    else:
                        # Recurse deeper
                        scan(entry, depth + 1)

            except PermissionError:
                pass

        scan(root_path, 0)
        return sorted(repos)
