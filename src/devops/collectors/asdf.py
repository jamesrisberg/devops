"""asdf version manager collector."""

import os
import subprocess
from pathlib import Path

from devops.collectors.base import BaseCollector, EnvEntry, Status


class AsdfCollector(BaseCollector):
    """Collects versions from asdf version manager."""

    @staticmethod
    def is_available() -> bool:
        """Check if asdf has installed plugins.

        Only uses fast filesystem checks - no subprocess calls.
        """
        asdf_dir = os.environ.get("ASDF_DATA_DIR", str(Path.home() / ".asdf"))
        plugins_dir = Path(asdf_dir) / "plugins"
        try:
            if plugins_dir.exists() and any(plugins_dir.iterdir()):
                return True
        except (PermissionError, OSError):
            pass

        return False

    def collect(self) -> list[EnvEntry]:
        """Collect all asdf plugins and their installed versions."""
        entries = []

        try:
            # Get list of installed plugins
            result = subprocess.run(
                ["asdf", "plugin", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return entries

            plugins = result.stdout.strip().split("\n")

            for plugin in plugins:
                if not plugin:
                    continue

                plugin = plugin.strip()
                versions = self._get_versions(plugin)

                if versions:
                    entries.append(
                        EnvEntry(
                            name=f"asdf: {plugin}",
                            status=Status.HEALTHY,
                            details={
                                "plugin": plugin,
                                "versions": versions,
                                "version_count": len(versions),
                            },
                        )
                    )

        except Exception:
            pass

        return entries

    def _get_versions(self, plugin: str) -> list[dict]:
        """Get installed versions for a plugin."""
        versions = []

        try:
            result = subprocess.run(
                ["asdf", "list", plugin],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return versions

            # Get current version
            current = ""
            current_result = subprocess.run(
                ["asdf", "current", plugin],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if current_result.returncode == 0:
                parts = current_result.stdout.split()
                if len(parts) >= 2:
                    current = parts[1]

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                version = line.strip()
                # Remove leading asterisk or spaces
                version = version.lstrip("* ")

                if version:
                    versions.append(
                        {
                            "version": version,
                            "is_current": version == current,
                        }
                    )

        except Exception:
            pass

        return versions
