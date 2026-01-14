"""Async-compatible Homebrew collector for use with Textual workers."""

import json
import subprocess
from dataclasses import dataclass

from devops.cache.brew_list_cache import CacheKey, get_brew_list_cache
from devops.collectors.base import EnvEntry, Status


@dataclass
class BrewCollectResult:
    """Result from collecting brew data."""

    formulae: list[dict]
    casks: list[dict]
    outdated: list[dict]
    from_cache: bool = False


def collect_formulae_sync() -> list[dict]:
    """Synchronously collect formulae list."""
    try:
        result = subprocess.run(
            ["brew", "list", "--formula", "--json=v2"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            formulae = []
            for f in data.get("formulae", []):
                formulae.append(
                    {
                        "name": f.get("name", ""),
                        "version": (
                            f.get("installed", [{}])[0].get("version", "")
                            if f.get("installed")
                            else ""
                        ),
                        "desc": f.get("desc", ""),
                        "homepage": f.get("homepage", ""),
                    }
                )
            return sorted(formulae, key=lambda x: x["name"])
    except Exception:
        pass

    # Fallback to simple list
    try:
        result = subprocess.run(
            ["brew", "list", "--formula"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return [
                {"name": p.strip(), "version": "", "desc": ""}
                for p in result.stdout.strip().split("\n")
                if p.strip()
            ]
    except Exception:
        pass
    return []


def collect_casks_sync() -> list[dict]:
    """Synchronously collect casks list."""
    try:
        result = subprocess.run(
            ["brew", "list", "--cask"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return [
                {"name": p.strip(), "version": "", "desc": "GUI Application"}
                for p in result.stdout.strip().split("\n")
                if p.strip()
            ]
    except Exception:
        pass
    return []


def collect_outdated_sync() -> list[dict]:
    """Synchronously collect outdated packages."""
    try:
        result = subprocess.run(
            ["brew", "outdated", "--json=v2"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            outdated = []
            for f in data.get("formulae", []):
                outdated.append(
                    {
                        "name": f.get("name", ""),
                        "current": (
                            f.get("installed_versions", [""])[0]
                            if f.get("installed_versions")
                            else ""
                        ),
                        "latest": f.get("current_version", ""),
                    }
                )
            for c in data.get("casks", []):
                outdated.append(
                    {
                        "name": c.get("name", ""),
                        "current": c.get("installed_versions", ""),
                        "latest": c.get("current_version", ""),
                    }
                )
            return outdated
    except Exception:
        pass
    return []


def collect_all_sync(use_cache: bool = True) -> BrewCollectResult:
    """Collect all brew data synchronously.

    This is designed to be called from a Textual thread worker.
    """
    cache = get_brew_list_cache()

    # Try cache first
    if use_cache:
        cached_formulae = cache.get(CacheKey.FORMULAE)
        cached_casks = cache.get(CacheKey.CASKS)
        cached_outdated = cache.get(CacheKey.OUTDATED)

        if cached_formulae is not None and cached_casks is not None:
            return BrewCollectResult(
                formulae=cached_formulae,
                casks=cached_casks,
                outdated=cached_outdated or [],
                from_cache=True,
            )

    # Fetch fresh data
    formulae = collect_formulae_sync()
    casks = collect_casks_sync()
    outdated = collect_outdated_sync()

    # Update cache
    cache.set(CacheKey.FORMULAE, formulae)
    cache.set(CacheKey.CASKS, casks)
    cache.set(CacheKey.OUTDATED, outdated)

    return BrewCollectResult(
        formulae=formulae,
        casks=casks,
        outdated=outdated,
        from_cache=False,
    )


def build_entries_from_result(result: BrewCollectResult) -> list[EnvEntry]:
    """Convert BrewCollectResult to EnvEntry list for the UI."""
    entries = []

    if result.formulae:
        entries.append(
            EnvEntry(
                name="Formulae",
                path="/opt/homebrew/Cellar",
                status=Status.HEALTHY,
                details={
                    "type": "category",
                    "description": "Command-line packages",
                    "count": len(result.formulae),
                    "packages": result.formulae,
                },
            )
        )

    if result.casks:
        entries.append(
            EnvEntry(
                name="Casks",
                path="/opt/homebrew/Caskroom",
                status=Status.HEALTHY,
                details={
                    "type": "category",
                    "description": "GUI applications",
                    "count": len(result.casks),
                    "packages": result.casks,
                },
            )
        )

    if result.outdated:
        entries.append(
            EnvEntry(
                name=f"Outdated ({len(result.outdated)})",
                path="",
                status=Status.WARNING,
                details={
                    "type": "outdated",
                    "description": "Packages with available updates",
                    "count": len(result.outdated),
                    "packages": result.outdated,
                },
            )
        )

    return entries
