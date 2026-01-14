"""Cache for man pages keyed by package name and version."""

import json
import subprocess
from pathlib import Path


class ManPageCache:
    """Cache man pages with version-based invalidation."""

    def __init__(self):
        self._cache_dir = Path.home() / ".cache" / "devops"
        self._cache_file = self._cache_dir / "man_pages.json"
        self._cache: dict[str, dict] = {}  # {package: {version: str, content: str}}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load cache from disk."""
        try:
            if self._cache_file.exists():
                with open(self._cache_file, "r") as f:
                    self._cache = json.load(f)
        except Exception:
            self._cache = {}

    def _save_to_disk(self) -> None:
        """Save cache to disk."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self._cache_file, "w") as f:
                json.dump(self._cache, f)
        except Exception:
            pass

    def get(self, package_name: str, version: str) -> str | None:
        """Get cached man page if version matches."""
        entry = self._cache.get(package_name)
        if entry and entry.get("version") == version:
            return entry.get("content")
        return None

    def set(self, package_name: str, version: str, content: str) -> None:
        """Cache man page content for a package version."""
        self._cache[package_name] = {"version": version, "content": content}
        self._save_to_disk()

    def fetch_and_cache(self, package_name: str, version: str) -> str | None:
        """Fetch man page and cache it. Returns content or None."""
        # Check cache first
        cached = self.get(package_name, version)
        if cached:
            return cached

        # Fetch from system
        try:
            result = subprocess.run(
                ["man", "-P", "cat", package_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                # Truncate to first 100 lines for storage
                lines = result.stdout.strip().split("\n")[:100]
                content = "\n".join(lines)
                self.set(package_name, version, content)
                return content
        except Exception:
            pass
        return None


# Singleton
_man_cache: ManPageCache | None = None


def get_man_cache() -> ManPageCache:
    """Get the singleton man page cache instance."""
    global _man_cache
    if _man_cache is None:
        _man_cache = ManPageCache()
    return _man_cache
