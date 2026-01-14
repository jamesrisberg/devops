"""Persistent cache for Homebrew package lists with smart invalidation."""

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path


class CacheKey(Enum):
    """Cache keys for different brew data types."""

    FORMULAE = "formulae"
    CASKS = "casks"
    OUTDATED = "outdated"


@dataclass
class CacheEntry:
    """A cached entry with metadata for invalidation."""

    data: list[dict]
    brew_prefix_hash: str  # Hash of Cellar mtime to detect changes

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CacheEntry":
        return cls(data=d["data"], brew_prefix_hash=d["brew_prefix_hash"])


class BrewListCache:
    """Cache for brew list results with event-based invalidation."""

    def __init__(self):
        self._cache_dir = Path.home() / ".cache" / "devops"
        self._cache_file = self._cache_dir / "brew_lists.json"
        self._cache: dict[str, CacheEntry] = {}
        self._dirty = False
        self._load_from_disk()

    def _get_brew_prefix_hash(self) -> str:
        """Get a hash representing the current homebrew state."""
        # Hash based on Cellar directory modification time
        cellar = Path("/opt/homebrew/Cellar")
        if not cellar.exists():
            # Try Intel Mac location
            cellar = Path("/usr/local/Cellar")
        if cellar.exists():
            return hashlib.md5(str(cellar.stat().st_mtime).encode()).hexdigest()[:8]
        return "unknown"

    def _load_from_disk(self) -> None:
        """Load cache from disk."""
        try:
            if self._cache_file.exists():
                with open(self._cache_file, "r") as f:
                    data = json.load(f)
                    self._cache = {k: CacheEntry.from_dict(v) for k, v in data.items()}
        except Exception:
            self._cache = {}

    def _save_to_disk(self) -> None:
        """Save cache to disk."""
        if not self._dirty:
            return
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self._cache_file, "w") as f:
                json.dump({k: v.to_dict() for k, v in self._cache.items()}, f)
            self._dirty = False
        except Exception:
            pass

    def get(self, key: CacheKey) -> list[dict] | None:
        """Get cached data if valid."""
        entry = self._cache.get(key.value)
        if entry:
            # Check if brew prefix changed significantly
            current_hash = self._get_brew_prefix_hash()
            if entry.brew_prefix_hash == current_hash:
                return entry.data
        return None

    def set(self, key: CacheKey, data: list[dict]) -> None:
        """Cache data with current brew state."""
        self._cache[key.value] = CacheEntry(
            data=data, brew_prefix_hash=self._get_brew_prefix_hash()
        )
        self._dirty = True
        self._save_to_disk()

    def invalidate(self, key: CacheKey) -> None:
        """Invalidate a specific cache entry."""
        if key.value in self._cache:
            del self._cache[key.value]
            self._dirty = True
            self._save_to_disk()

    def invalidate_all(self) -> None:
        """Invalidate all cache entries."""
        self._cache.clear()
        self._dirty = True
        self._save_to_disk()

    def invalidate_for_install(self) -> None:
        """Invalidate caches affected by install/uninstall."""
        self.invalidate(CacheKey.FORMULAE)
        self.invalidate(CacheKey.CASKS)
        self.invalidate(CacheKey.OUTDATED)

    def invalidate_for_update(self) -> None:
        """Invalidate caches affected by brew update."""
        self.invalidate(CacheKey.OUTDATED)

    def invalidate_for_upgrade(self, package_name: str) -> None:
        """Invalidate caches affected by upgrading a package."""
        self.invalidate(CacheKey.OUTDATED)
        # Also invalidate the package info cache
        from devops.cache.brew_cache import get_brew_cache

        brew_cache = get_brew_cache()
        if package_name in brew_cache._cache:
            del brew_cache._cache[package_name]
            brew_cache._save_to_disk()


# Singleton
_brew_list_cache: BrewListCache | None = None


def get_brew_list_cache() -> BrewListCache:
    """Get the singleton brew list cache instance."""
    global _brew_list_cache
    if _brew_list_cache is None:
        _brew_list_cache = BrewListCache()
    return _brew_list_cache
