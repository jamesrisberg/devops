"""Node.js environment collector for nvm, fnm, volta, and system installs."""

import json
import os
import subprocess
from pathlib import Path

from devops.collectors.base import BaseCollector, EnvEntry, Status


class NodeCollector(BaseCollector):
    """Collects Node.js installations from various version managers."""

    @staticmethod
    def is_available() -> bool:
        """Check if any Node.js version manager has actual installed versions.

        Only uses fast filesystem checks - no subprocess calls.
        """
        # Check for nvm with actual versions installed
        nvm_dir = os.environ.get("NVM_DIR", str(Path.home() / ".nvm"))
        nvm_versions = Path(nvm_dir) / "versions" / "node"
        try:
            if nvm_versions.exists() and any(nvm_versions.iterdir()):
                return True
        except (PermissionError, OSError):
            pass

        # Check for fnm with actual versions installed
        fnm_versions = Path.home() / ".fnm" / "node-versions"
        try:
            if fnm_versions.exists() and any(fnm_versions.iterdir()):
                return True
        except (PermissionError, OSError):
            pass

        # Check for volta with actual versions installed
        volta_home = os.environ.get("VOLTA_HOME", str(Path.home() / ".volta"))
        volta_versions = Path(volta_home) / "tools" / "image" / "node"
        try:
            if volta_versions.exists() and any(volta_versions.iterdir()):
                return True
        except (PermissionError, OSError):
            pass

        # Check for homebrew node via filesystem (fast)
        homebrew_node = Path("/opt/homebrew/bin/node")
        if homebrew_node.exists():
            return True
        # Intel Mac path
        homebrew_node_intel = Path("/usr/local/bin/node")
        if homebrew_node_intel.exists():
            return True

        return False

    def collect(self) -> list[EnvEntry]:
        """Collect all Node.js installations."""
        entries = []
        manager = self._detect_manager()

        if manager == "nvm":
            entries.extend(self._collect_nvm())
        elif manager == "fnm":
            entries.extend(self._collect_fnm())
        elif manager == "volta":
            entries.extend(self._collect_volta())
        elif manager == "homebrew":
            entries.extend(self._collect_homebrew())
        elif manager == "system":
            entries.extend(self._collect_system())

        return entries

    def _detect_manager(self) -> str:
        """Detect which Node.js manager is in use."""
        nvm_dir = os.environ.get("NVM_DIR", str(Path.home() / ".nvm"))
        if Path(nvm_dir).exists() and (Path(nvm_dir) / "versions" / "node").exists():
            return "nvm"

        fnm_dir = Path.home() / ".fnm"
        if fnm_dir.exists():
            return "fnm"

        volta_home = os.environ.get("VOLTA_HOME", str(Path.home() / ".volta"))
        if Path(volta_home).exists():
            return "volta"

        try:
            result = subprocess.run(
                ["brew", "list", "node"], capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return "homebrew"
        except Exception:
            pass

        return "system"

    def _collect_nvm(self) -> list[EnvEntry]:
        """Collect Node.js versions from nvm."""
        entries = []
        nvm_dir = os.environ.get("NVM_DIR", str(Path.home() / ".nvm"))
        versions_dir = Path(nvm_dir) / "versions" / "node"

        if not versions_dir.exists():
            return entries

        # Get current version
        current = ""
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                current = result.stdout.strip()
        except Exception:
            pass

        for version_dir in sorted(versions_dir.iterdir(), reverse=True):
            if version_dir.is_dir():
                version = version_dir.name
                is_current = version == current or f"v{version}" == current
                packages = self._get_global_packages(version_dir / "bin" / "npm")

                entries.append(
                    EnvEntry(
                        name=f"Node {version}",
                        status=Status.HEALTHY,
                        details={
                            "version": version,
                            "path": str(version_dir),
                            "manager": "nvm",
                            "is_current": is_current,
                            "packages": packages,
                            "package_count": len(packages),
                        },
                    )
                )

        return entries

    def _collect_fnm(self) -> list[EnvEntry]:
        """Collect Node.js versions from fnm."""
        entries = []
        fnm_dir = Path.home() / ".fnm" / "node-versions"

        if not fnm_dir.exists():
            return entries

        current = ""
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                current = result.stdout.strip()
        except Exception:
            pass

        for version_dir in sorted(fnm_dir.iterdir(), reverse=True):
            if version_dir.is_dir():
                version = version_dir.name
                is_current = version == current or f"v{version}" == current
                npm_path = version_dir / "installation" / "bin" / "npm"
                packages = self._get_global_packages(npm_path)

                entries.append(
                    EnvEntry(
                        name=f"Node {version}",
                        status=Status.HEALTHY,
                        details={
                            "version": version,
                            "path": str(version_dir),
                            "manager": "fnm",
                            "is_current": is_current,
                            "packages": packages,
                            "package_count": len(packages),
                        },
                    )
                )

        return entries

    def _collect_volta(self) -> list[EnvEntry]:
        """Collect Node.js versions from volta."""
        entries = []
        volta_home = os.environ.get("VOLTA_HOME", str(Path.home() / ".volta"))
        tools_dir = Path(volta_home) / "tools" / "image" / "node"

        if not tools_dir.exists():
            return entries

        current = ""
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                current = result.stdout.strip()
        except Exception:
            pass

        for version_dir in sorted(tools_dir.iterdir(), reverse=True):
            if version_dir.is_dir():
                version = version_dir.name
                is_current = version == current or f"v{version}" == current
                packages = self._get_global_packages(version_dir / "bin" / "npm")

                entries.append(
                    EnvEntry(
                        name=f"Node {version}",
                        status=Status.HEALTHY,
                        details={
                            "version": version,
                            "path": str(version_dir),
                            "manager": "volta",
                            "is_current": is_current,
                            "packages": packages,
                            "package_count": len(packages),
                        },
                    )
                )

        return entries

    def _collect_homebrew(self) -> list[EnvEntry]:
        """Collect Homebrew-installed Node.js."""
        entries = []
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                packages = self._get_global_packages_system()

                entries.append(
                    EnvEntry(
                        name=f"Homebrew Node {version}",
                        status=Status.HEALTHY,
                        details={
                            "version": version,
                            "path": "/opt/homebrew/bin/node",
                            "manager": "homebrew",
                            "is_current": True,
                            "packages": packages,
                            "package_count": len(packages),
                        },
                    )
                )
        except Exception:
            pass

        return entries

    def _collect_system(self) -> list[EnvEntry]:
        """Collect system Node.js."""
        entries = []
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()

                which_result = subprocess.run(
                    ["which", "node"], capture_output=True, text=True, timeout=5
                )
                node_path = (
                    which_result.stdout.strip()
                    if which_result.returncode == 0
                    else "/usr/bin/node"
                )

                packages = self._get_global_packages_system()

                entries.append(
                    EnvEntry(
                        name=f"System Node {version}",
                        status=Status.HEALTHY,
                        details={
                            "version": version,
                            "path": node_path,
                            "manager": "system",
                            "is_current": True,
                            "packages": packages,
                            "package_count": len(packages),
                        },
                    )
                )
        except Exception:
            pass

        return entries

    def _get_global_packages(self, npm_path: Path) -> list[dict]:
        """Get global npm packages for a specific npm installation."""
        if not npm_path.exists():
            return []

        try:
            result = subprocess.run(
                [str(npm_path), "list", "-g", "--json", "--depth=0"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                deps = data.get("dependencies", {})
                return [
                    {"name": name, "version": info.get("version", "")}
                    for name, info in deps.items()
                ]
        except Exception:
            pass

        return []

    def _get_global_packages_system(self) -> list[dict]:
        """Get global npm packages from system npm."""
        try:
            result = subprocess.run(
                ["npm", "list", "-g", "--json", "--depth=0"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                deps = data.get("dependencies", {})
                return [
                    {"name": name, "version": info.get("version", "")}
                    for name, info in deps.items()
                ]
        except Exception:
            pass

        return []
