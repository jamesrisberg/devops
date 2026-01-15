"""Git repository cache for fast loading."""

import json
from datetime import datetime
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "devops"
CACHE_FILE = CACHE_DIR / "git_repos.json"


def _ensure_cache_dir() -> None:
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_cache_data() -> dict:
    """Load raw cache data."""
    if not CACHE_FILE.exists():
        return {"repos": [], "scan_dirs": []}

    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
            # Ensure both keys exist
            if "repos" not in data:
                data["repos"] = []
            if "scan_dirs" not in data:
                data["scan_dirs"] = []
            return data
    except (json.JSONDecodeError, IOError):
        return {"repos": [], "scan_dirs": []}


def _save_cache_data(data: dict) -> None:
    """Save raw cache data."""
    _ensure_cache_dir()
    data["last_updated"] = datetime.now().isoformat()
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_cached_repos() -> list[str]:
    """Load cached repository paths."""
    return _load_cache_data().get("repos", [])


def load_scan_dirs() -> list[str]:
    """Load saved scan directories."""
    return _load_cache_data().get("scan_dirs", [])


def save_repos(repos: list[str]) -> None:
    """Save repository paths to cache."""
    data = _load_cache_data()
    data["repos"] = repos
    _save_cache_data(data)


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


def add_scan_dir(path: str) -> list[str]:
    """Add a scan directory. Returns updated list."""
    data = _load_cache_data()
    scan_dirs = data.get("scan_dirs", [])

    # Normalize path
    normalized = str(Path(path).expanduser().resolve())

    if normalized not in scan_dirs:
        scan_dirs.append(normalized)
        scan_dirs.sort()
        data["scan_dirs"] = scan_dirs
        _save_cache_data(data)

    return scan_dirs


def remove_scan_dir(path: str) -> list[str]:
    """Remove a scan directory. Returns updated list."""
    data = _load_cache_data()
    scan_dirs = data.get("scan_dirs", [])

    # Normalize path
    normalized = str(Path(path).expanduser().resolve())

    if normalized in scan_dirs:
        scan_dirs.remove(normalized)
        data["scan_dirs"] = scan_dirs
        _save_cache_data(data)

    return scan_dirs
