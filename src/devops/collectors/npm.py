"""NPM package collector."""

import json
import os
import subprocess
from pathlib import Path

from devops.collectors.base import BaseCollector, EnvEntry, Status


class NpmCollector(BaseCollector):
    """Collects NPM packages (global and local)."""

    def collect(self) -> list[EnvEntry]:
        """Collect all NPM packages."""
        entries = []

        # Check for outdated global packages
        outdated_pkgs = self._get_outdated_global()
        if outdated_pkgs:
            entries.append(
                EnvEntry(
                    name=f"Outdated ({len(outdated_pkgs)})",
                    path="npm outdated",
                    status=Status.WARNING,
                    details={
                        "type": "outdated",
                        "packages": outdated_pkgs,
                        "count": len(outdated_pkgs),
                    },
                )
            )

        # Global packages
        global_pkgs = self._get_global_packages()
        if global_pkgs:
            entries.append(
                EnvEntry(
                    name="Global Packages",
                    path="npm global",
                    status=Status.HEALTHY,
                    details={
                        "type": "global",
                        "packages": global_pkgs,
                        "package_count": len(global_pkgs),
                    },
                )
            )

        # Local packages (if in an npm project)
        local_pkgs = self._get_local_packages()
        if local_pkgs:
            cwd = os.getcwd()
            entries.append(
                EnvEntry(
                    name=f"Local: {Path(cwd).name}",
                    path=cwd,
                    status=Status.HEALTHY,
                    details={
                        "type": "local",
                        "packages": local_pkgs,
                        "package_count": len(local_pkgs),
                        "project_path": cwd,
                    },
                )
            )

        return entries

    def _get_outdated_global(self) -> list[dict]:
        """Get outdated global npm packages."""
        try:
            result = subprocess.run(
                ["npm", "outdated", "-g", "--json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # npm outdated returns exit code 1 when there are outdated packages
            if result.stdout:
                data = json.loads(result.stdout)
                return [
                    {
                        "name": name,
                        "current": info.get("current", ""),
                        "wanted": info.get("wanted", ""),
                        "latest": info.get("latest", ""),
                    }
                    for name, info in data.items()
                ]
        except Exception:
            pass

        return []

    def _get_global_packages(self) -> list[dict]:
        """Get globally installed npm packages."""
        try:
            result = subprocess.run(
                ["npm", "list", "-g", "--json", "--depth=0"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0 or result.stdout:
                data = json.loads(result.stdout)
                deps = data.get("dependencies", {})
                return [
                    {"name": name, "version": info.get("version", "")}
                    for name, info in deps.items()
                ]
        except Exception:
            pass

        return []

    def _get_local_packages(self) -> list[dict]:
        """Get local npm packages if in an npm project."""
        # Check if package.json exists in current directory
        if not Path("package.json").exists():
            return []

        try:
            result = subprocess.run(
                ["npm", "list", "--json", "--depth=0"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0 or result.stdout:
                data = json.loads(result.stdout)
                deps = data.get("dependencies", {})
                return [
                    {"name": name, "version": info.get("version", "")}
                    for name, info in deps.items()
                ]
        except Exception:
            pass

        return []
