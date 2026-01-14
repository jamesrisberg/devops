"""Ruby environment collector for rbenv, chruby, and system installs."""

import os
import subprocess
from pathlib import Path

from devops.collectors.base import BaseCollector, EnvEntry, Status


class RubyCollector(BaseCollector):
    """Collects Ruby installations from various version managers."""

    @staticmethod
    def is_available() -> bool:
        """Check if any Ruby version manager has actual installed versions.

        Only uses fast filesystem checks - no subprocess calls.
        """
        # Check for rbenv with actual versions installed
        rbenv_root = os.environ.get("RBENV_ROOT", str(Path.home() / ".rbenv"))
        rbenv_versions = Path(rbenv_root) / "versions"
        try:
            if rbenv_versions.exists() and any(rbenv_versions.iterdir()):
                return True
        except (PermissionError, OSError):
            pass

        # Check for chruby with actual versions installed
        chruby_dir = Path("/opt/rubies")
        try:
            if chruby_dir.exists() and any(chruby_dir.iterdir()):
                return True
        except (PermissionError, OSError):
            pass
        chruby_home = Path.home() / ".rubies"
        try:
            if chruby_home.exists() and any(chruby_home.iterdir()):
                return True
        except (PermissionError, OSError):
            pass

        # Check for homebrew ruby via filesystem (fast)
        homebrew_ruby = Path("/opt/homebrew/opt/ruby/bin/ruby")
        if homebrew_ruby.exists():
            return True
        # Intel Mac path
        homebrew_ruby_intel = Path("/usr/local/opt/ruby/bin/ruby")
        if homebrew_ruby_intel.exists():
            return True

        # Don't show tab for system ruby - it's not useful to display
        return False

    def collect(self) -> list[EnvEntry]:
        """Collect all Ruby installations."""
        entries = []
        manager = self._detect_manager()

        if manager == "rbenv":
            entries.extend(self._collect_rbenv())
        elif manager == "chruby":
            entries.extend(self._collect_chruby())
        elif manager == "homebrew":
            entries.extend(self._collect_homebrew())
        elif manager == "system":
            entries.extend(self._collect_system())

        return entries

    def _detect_manager(self) -> str:
        """Detect which Ruby manager is in use."""
        rbenv_root = os.environ.get("RBENV_ROOT", str(Path.home() / ".rbenv"))
        if Path(rbenv_root).exists() and (Path(rbenv_root) / "versions").exists():
            return "rbenv"

        chruby_dir = Path("/opt/rubies")
        chruby_home = Path.home() / ".rubies"
        if chruby_dir.exists() or chruby_home.exists():
            return "chruby"

        try:
            result = subprocess.run(
                ["brew", "list", "ruby"], capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return "homebrew"
        except Exception:
            pass

        return "system"

    def _collect_rbenv(self) -> list[EnvEntry]:
        """Collect Ruby versions from rbenv."""
        entries = []
        rbenv_root = os.environ.get("RBENV_ROOT", str(Path.home() / ".rbenv"))
        versions_dir = Path(rbenv_root) / "versions"

        if not versions_dir.exists():
            return entries

        # Get current version
        current = ""
        try:
            result = subprocess.run(
                ["rbenv", "version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                current = result.stdout.split()[0]
        except Exception:
            pass

        for version_dir in sorted(versions_dir.iterdir(), reverse=True):
            if version_dir.is_dir():
                version = version_dir.name
                is_current = version == current
                gems = self._get_gems(version_dir / "bin" / "gem")

                entries.append(
                    EnvEntry(
                        name=f"Ruby {version}",
                        status=Status.HEALTHY,
                        details={
                            "version": version,
                            "path": str(version_dir),
                            "manager": "rbenv",
                            "is_current": is_current,
                            "gems": gems,
                            "gem_count": len(gems),
                        },
                    )
                )

        return entries

    def _collect_chruby(self) -> list[EnvEntry]:
        """Collect Ruby versions from chruby."""
        entries = []
        rubies_dirs = [Path("/opt/rubies"), Path.home() / ".rubies"]

        current = ""
        try:
            result = subprocess.run(
                ["ruby", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                current = result.stdout.split()[1]
        except Exception:
            pass

        for rubies_dir in rubies_dirs:
            if not rubies_dir.exists():
                continue

            for version_dir in sorted(rubies_dir.iterdir(), reverse=True):
                if version_dir.is_dir():
                    version = version_dir.name
                    is_current = current in version
                    gems = self._get_gems(version_dir / "bin" / "gem")

                    entries.append(
                        EnvEntry(
                            name=f"Ruby {version}",
                            status=Status.HEALTHY,
                            details={
                                "version": version,
                                "path": str(version_dir),
                                "manager": "chruby",
                                "is_current": is_current,
                                "gems": gems,
                                "gem_count": len(gems),
                            },
                        )
                    )

        return entries

    def _collect_homebrew(self) -> list[EnvEntry]:
        """Collect Homebrew-installed Ruby."""
        entries = []
        try:
            result = subprocess.run(
                ["ruby", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.split()[1]
                gems = self._get_gems_system()

                entries.append(
                    EnvEntry(
                        name=f"Homebrew Ruby {version}",
                        status=Status.HEALTHY,
                        details={
                            "version": version,
                            "path": "/opt/homebrew/bin/ruby",
                            "manager": "homebrew",
                            "is_current": True,
                            "gems": gems,
                            "gem_count": len(gems),
                        },
                    )
                )
        except Exception:
            pass

        return entries

    def _collect_system(self) -> list[EnvEntry]:
        """Collect system Ruby."""
        entries = []
        try:
            result = subprocess.run(
                ["ruby", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.split()[1]

                which_result = subprocess.run(
                    ["which", "ruby"], capture_output=True, text=True, timeout=5
                )
                ruby_path = (
                    which_result.stdout.strip()
                    if which_result.returncode == 0
                    else "/usr/bin/ruby"
                )

                gems = self._get_gems_system()

                entries.append(
                    EnvEntry(
                        name=f"System Ruby {version}",
                        status=Status.HEALTHY,
                        details={
                            "version": version,
                            "path": ruby_path,
                            "manager": "system",
                            "is_current": True,
                            "gems": gems,
                            "gem_count": len(gems),
                        },
                    )
                )
        except Exception:
            pass

        return entries

    def _get_gems(self, gem_path: Path) -> list[dict]:
        """Get installed gems for a specific Ruby installation."""
        if not gem_path.exists():
            return []

        try:
            result = subprocess.run(
                [str(gem_path), "list", "--no-details"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                gems = []
                for line in result.stdout.strip().split("\n"):
                    if line and " " in line:
                        parts = line.split(" ", 1)
                        name = parts[0]
                        version = (
                            parts[1].strip("()").split(",")[0] if len(parts) > 1 else ""
                        )
                        gems.append({"name": name, "version": version})
                return gems
        except Exception:
            pass

        return []

    def _get_gems_system(self) -> list[dict]:
        """Get installed gems from system gem."""
        try:
            result = subprocess.run(
                ["gem", "list", "--no-details"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                gems = []
                for line in result.stdout.strip().split("\n"):
                    if line and " " in line:
                        parts = line.split(" ", 1)
                        name = parts[0]
                        version = (
                            parts[1].strip("()").split(",")[0] if len(parts) > 1 else ""
                        )
                        gems.append({"name": name, "version": version})
                return gems
        except Exception:
            pass

        return []
