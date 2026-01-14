import subprocess
import json
from pathlib import Path

from devops.collectors.base import BaseCollector, EnvEntry, Status


class HomebrewCollector(BaseCollector):
    """Collector for Homebrew packages."""

    name = "Homebrew"
    description = "Homebrew packages and casks"

    def collect(self) -> list[EnvEntry]:
        """Collect Homebrew package information."""
        entries = []

        # Get formulae (CLI packages)
        formulae = self._get_formulae()
        if formulae:
            entry = EnvEntry(
                name="Formulae",
                path="/opt/homebrew/Cellar",
                status=Status.HEALTHY,
                details={
                    "type": "category",
                    "description": "Command-line packages",
                    "count": len(formulae),
                    "packages": formulae,
                }
            )
            entries.append(entry)

        # Get casks (GUI apps)
        casks = self._get_casks()
        if casks:
            entry = EnvEntry(
                name="Casks",
                path="/opt/homebrew/Caskroom",
                status=Status.HEALTHY,
                details={
                    "type": "category",
                    "description": "GUI applications",
                    "count": len(casks),
                    "packages": casks,
                }
            )
            entries.append(entry)

        # Check for issues
        outdated = self._get_outdated()
        if outdated:
            entry = EnvEntry(
                name=f"Outdated ({len(outdated)})",
                path="",
                status=Status.WARNING,
                details={
                    "type": "outdated",
                    "description": "Packages with available updates",
                    "count": len(outdated),
                    "packages": outdated,
                }
            )
            entries.append(entry)

        return entries

    def _get_formulae(self) -> list[dict]:
        """Get installed formulae."""
        try:
            result = subprocess.run(
                ["brew", "list", "--formula", "--json=v2"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                formulae = []
                for f in data.get("formulae", []):
                    formulae.append({
                        "name": f.get("name", ""),
                        "version": f.get("installed", [{}])[0].get("version", "") if f.get("installed") else "",
                        "desc": f.get("desc", ""),
                        "homepage": f.get("homepage", ""),
                    })
                return sorted(formulae, key=lambda x: x["name"])
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        # Fallback to simple list
        try:
            result = subprocess.run(
                ["brew", "list", "--formula"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return [{"name": p.strip(), "version": "", "desc": ""} 
                        for p in result.stdout.strip().split("\n") if p.strip()]
        except:
            pass
        return []

    def _get_casks(self) -> list[dict]:
        """Get installed casks."""
        try:
            result = subprocess.run(
                ["brew", "list", "--cask"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return [{"name": p.strip(), "version": "", "desc": "GUI Application"} 
                        for p in result.stdout.strip().split("\n") if p.strip()]
        except:
            pass
        return []

    def _get_outdated(self) -> list[dict]:
        """Get outdated packages."""
        try:
            result = subprocess.run(
                ["brew", "outdated", "--json=v2"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                outdated = []
                for f in data.get("formulae", []):
                    outdated.append({
                        "name": f.get("name", ""),
                        "current": f.get("installed_versions", [""])[0] if f.get("installed_versions") else "",
                        "latest": f.get("current_version", ""),
                    })
                for c in data.get("casks", []):
                    outdated.append({
                        "name": c.get("name", ""),
                        "current": c.get("installed_versions", ""),
                        "latest": c.get("current_version", ""),
                    })
                return outdated
        except:
            pass
        return []
