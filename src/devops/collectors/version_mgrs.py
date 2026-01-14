import subprocess
import os
from pathlib import Path

from devops.collectors.base import BaseCollector, EnvEntry, Status


class VersionManagerCollector(BaseCollector):
    """Collector for version managers (nvm, pyenv, rbenv, etc)."""

    name = "Version Managers"
    description = "Language version managers"

    def collect(self) -> list[EnvEntry]:
        """Collect version manager information."""
        entries = []

        # Check for nvm
        nvm = self._check_nvm()
        if nvm:
            entries.append(nvm)

        # Check for pyenv
        pyenv = self._check_pyenv()
        if pyenv:
            entries.append(pyenv)

        # Check for rbenv
        rbenv = self._check_rbenv()
        if rbenv:
            entries.append(rbenv)

        # Check for asdf
        asdf = self._check_asdf()
        if asdf:
            entries.append(asdf)

        # Check for volta (Node)
        volta = self._check_volta()
        if volta:
            entries.append(volta)

        # Check for fnm (Fast Node Manager)
        fnm = self._check_fnm()
        if fnm:
            entries.append(fnm)

        # Check for sdkman (Java/JVM)
        sdkman = self._check_sdkman()
        if sdkman:
            entries.append(sdkman)

        # Check for rustup (Rust)
        rustup = self._check_rustup()
        if rustup:
            entries.append(rustup)

        # Check for goenv (Go)
        goenv = self._check_goenv()
        if goenv:
            entries.append(goenv)

        if not entries:
            entries.append(EnvEntry(
                name="No version managers found",
                path="",
                status=Status.HEALTHY,
                details={
                    "description": "Version managers help you install and switch between different versions of languages like Node, Python, Ruby, etc.",
                    "examples": ["nvm (Node)", "pyenv (Python)", "rbenv (Ruby)", "asdf (multiple)"],
                }
            ))

        return entries

    def _check_nvm(self) -> EnvEntry | None:
        """Check for nvm installation."""
        nvm_dir = Path(os.environ.get("NVM_DIR", Path.home() / ".nvm"))
        if nvm_dir.exists():
            versions = []
            versions_dir = nvm_dir / "versions" / "node"
            if versions_dir.exists():
                versions = [v.name for v in versions_dir.iterdir() if v.is_dir()]

            # Get current version
            current = ""
            try:
                result = subprocess.run(
                    ["node", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                current = result.stdout.strip()
            except:
                pass

            return EnvEntry(
                name="nvm (Node Version Manager)",
                path=str(nvm_dir),
                status=Status.HEALTHY,
                details={
                    "type": "nvm",
                    "versions": versions,
                    "current": current,
                    "count": len(versions),
                }
            )
        return None

    def _check_pyenv(self) -> EnvEntry | None:
        """Check for pyenv installation."""
        pyenv_root = Path(os.environ.get("PYENV_ROOT", Path.home() / ".pyenv"))
        if pyenv_root.exists():
            versions = []
            versions_dir = pyenv_root / "versions"
            if versions_dir.exists():
                versions = [v.name for v in versions_dir.iterdir() if v.is_dir()]

            return EnvEntry(
                name="pyenv (Python Version Manager)",
                path=str(pyenv_root),
                status=Status.HEALTHY,
                details={
                    "type": "pyenv",
                    "versions": versions,
                    "count": len(versions),
                }
            )
        return None

    def _check_rbenv(self) -> EnvEntry | None:
        """Check for rbenv installation."""
        rbenv_root = Path(os.environ.get("RBENV_ROOT", Path.home() / ".rbenv"))
        if rbenv_root.exists():
            versions = []
            versions_dir = rbenv_root / "versions"
            if versions_dir.exists():
                versions = [v.name for v in versions_dir.iterdir() if v.is_dir()]

            return EnvEntry(
                name="rbenv (Ruby Version Manager)",
                path=str(rbenv_root),
                status=Status.HEALTHY,
                details={
                    "type": "rbenv",
                    "versions": versions,
                    "count": len(versions),
                }
            )
        return None

    def _check_asdf(self) -> EnvEntry | None:
        """Check for asdf installation."""
        asdf_dir = Path(os.environ.get("ASDF_DIR", Path.home() / ".asdf"))
        if asdf_dir.exists():
            plugins = []
            plugins_dir = asdf_dir / "plugins"
            if plugins_dir.exists():
                plugins = [p.name for p in plugins_dir.iterdir() if p.is_dir()]

            return EnvEntry(
                name="asdf (Multiple Runtime Version Manager)",
                path=str(asdf_dir),
                status=Status.HEALTHY,
                details={
                    "type": "asdf",
                    "plugins": plugins,
                    "count": len(plugins),
                }
            )
        return None

    def _check_volta(self) -> EnvEntry | None:
        """Check for volta installation."""
        volta_home = Path(os.environ.get("VOLTA_HOME", Path.home() / ".volta"))
        if volta_home.exists():
            return EnvEntry(
                name="Volta (JavaScript Tool Manager)",
                path=str(volta_home),
                status=Status.HEALTHY,
                details={
                    "type": "volta",
                }
            )
        return None
    def _check_fnm(self) -> EnvEntry | None:
        """Check for fnm (Fast Node Manager) installation."""
        fnm_dir = Path(os.environ.get("FNM_DIR", Path.home() / ".fnm"))
        if fnm_dir.exists():
            versions = []
            node_versions_dir = fnm_dir / "node-versions"
            if node_versions_dir.exists():
                versions = [v.name for v in node_versions_dir.iterdir() if v.is_dir()]

            return EnvEntry(
                name="fnm (Fast Node Manager)",
                path=str(fnm_dir),
                status=Status.HEALTHY,
                details={
                    "type": "fnm",
                    "versions": versions,
                    "count": len(versions),
                }
            )
        return None

    def _check_sdkman(self) -> EnvEntry | None:
        """Check for SDKMAN installation."""
        sdkman_dir = Path(os.environ.get("SDKMAN_DIR", Path.home() / ".sdkman"))
        if sdkman_dir.exists():
            candidates = []
            candidates_dir = sdkman_dir / "candidates"
            if candidates_dir.exists():
                candidates = [c.name for c in candidates_dir.iterdir() if c.is_dir()]

            return EnvEntry(
                name="SDKMAN (JVM Version Manager)",
                path=str(sdkman_dir),
                status=Status.HEALTHY,
                details={
                    "type": "sdkman",
                    "plugins": candidates,
                    "count": len(candidates),
                }
            )
        return None

    def _check_rustup(self) -> EnvEntry | None:
        """Check for rustup installation."""
        rustup_home = Path(os.environ.get("RUSTUP_HOME", Path.home() / ".rustup"))
        if rustup_home.exists():
            toolchains = []
            toolchains_dir = rustup_home / "toolchains"
            if toolchains_dir.exists():
                toolchains = [t.name for t in toolchains_dir.iterdir() if t.is_dir()]

            return EnvEntry(
                name="rustup (Rust Toolchain Manager)",
                path=str(rustup_home),
                status=Status.HEALTHY,
                details={
                    "type": "rustup",
                    "versions": toolchains,
                    "count": len(toolchains),
                }
            )
        return None

    def _check_goenv(self) -> EnvEntry | None:
        """Check for goenv installation."""
        goenv_root = Path(os.environ.get("GOENV_ROOT", Path.home() / ".goenv"))
        if goenv_root.exists():
            versions = []
            versions_dir = goenv_root / "versions"
            if versions_dir.exists():
                versions = [v.name for v in versions_dir.iterdir() if v.is_dir()]

            return EnvEntry(
                name="goenv (Go Version Manager)",
                path=str(goenv_root),
                status=Status.HEALTHY,
                details={
                    "type": "goenv",
                    "versions": versions,
                    "count": len(versions),
                }
            )
        return None
