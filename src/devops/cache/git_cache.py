"""Git repository cache for fast loading."""

import json
from datetime import datetime
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "devops"
CACHE_FILE = CACHE_DIR / "git_repos.json"


def _ensure_cache_dir() -> None:
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_cached_repos() -> list[str]:
    """Load cached repository paths."""
    if not CACHE_FILE.exists():
        return []

    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
            return data.get("repos", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_repos(repos: list[str]) -> None:
    """Save repository paths to cache."""
    _ensure_cache_dir()

    data = {"repos": repos, "last_updated": datetime.now().isoformat()}

    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_repo(path: str) -> list[str]:
    """Add a repository path to cache. Returns updated list."""
    repos = load_cached_repos()

    # Normalize path
    normalized = str(Path(path).expanduser().resolve())

    if normalized not in repos:
        repos.append(normalized)
        repos.sort()
        save_repos(repos)

    return repos


def add_repos(paths: list[str]) -> list[str]:
    """Add multiple repository paths to cache. Returns updated list."""
    repos = load_cached_repos()

    for path in paths:
        normalized = str(Path(path).expanduser().resolve())
        if normalized not in repos:
            repos.append(normalized)

    repos.sort()
    save_repos(repos)
    return repos


def remove_repo(path: str) -> list[str]:
    """Remove a repository path from cache. Returns updated list."""
    repos = load_cached_repos()

    # Normalize path
    normalized = str(Path(path).expanduser().resolve())

    if normalized in repos:
        repos.remove(normalized)
        save_repos(repos)

    return repos


def clear_cache() -> None:
    """Clear all cached repositories."""
    save_repos([])
