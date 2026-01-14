"""Persistent cache for Homebrew package info."""

import json
import subprocess
import time
from pathlib import Path
from threading import Thread
from typing import Callable


class BrewInfoCache:
    """Cache for brew info results with disk persistence."""

    # Cache TTL in seconds (24 hours)
    CACHE_TTL = 24 * 60 * 60

    def __init__(self):
        self._cache_dir = Path.home() / ".cache" / "devops"
        self._cache_file = self._cache_dir / "brew_info.json"
        self._cache: dict[str, dict] = {}
        self._loading = False
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load cache from disk."""
        try:
            if self._cache_file.exists():
                with open(self._cache_file, "r") as f:
                    data = json.load(f)
                    # Filter out expired entries
                    now = time.time()
                    self._cache = {
                        k: v
                        for k, v in data.items()
                        if now - v.get("timestamp", 0) < self.CACHE_TTL
                    }
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

    def get(self, package_name: str) -> str | None:
        """Get cached brew info for a package."""
        entry = self._cache.get(package_name)
        if entry:
            # Check if still valid
            if time.time() - entry.get("timestamp", 0) < self.CACHE_TTL:
                return entry.get("info")
            else:
                # Expired, remove it
                del self._cache[package_name]
        return None

    def set(self, package_name: str, info: str) -> None:
        """Cache brew info for a package."""
        self._cache[package_name] = {
            "info": info,
            "timestamp": time.time(),
        }
        self._save_to_disk()

    def has(self, package_name: str) -> bool:
        """Check if package is in cache and not expired."""
        return self.get(package_name) is not None

    def load_all_in_background(
        self,
        package_names: list[str],
        on_progress: Callable[[str, int, int], None] | None = None,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Load brew info for all packages in background thread.

        Args:
            package_names: List of package names to load
            on_progress: Callback(package_name, current, total) for progress updates
            on_complete: Callback when all loading is complete
        """
        if self._loading:
            return

        # Filter out packages already in cache
        to_load = [p for p in package_names if not self.has(p)]

        if not to_load:
            if on_complete:
                on_complete()
            return

        def load_thread():
            self._loading = True
            total = len(to_load)
            for i, name in enumerate(to_load):
                try:
                    result = subprocess.run(
                        ["brew", "info", name],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split("\n")[:20]
                        info = "\n".join(lines)
                        self.set(name, info)
                    if on_progress:
                        on_progress(name, i + 1, total)
                except Exception:
                    pass
            self._loading = False
            self._save_to_disk()
            if on_complete:
                on_complete()

        thread = Thread(target=load_thread, daemon=True)
        thread.start()

    @property
    def is_loading(self) -> bool:
        """Check if background loading is in progress."""
        return self._loading

    def clear(self) -> None:
        """Clear the cache."""
        self._cache = {}
        try:
            if self._cache_file.exists():
                self._cache_file.unlink()
        except Exception:
            pass


# Singleton instance
_brew_cache: BrewInfoCache | None = None


def get_brew_cache() -> BrewInfoCache:
    """Get the singleton brew cache instance."""
    global _brew_cache
    if _brew_cache is None:
        _brew_cache = BrewInfoCache()
    return _brew_cache
