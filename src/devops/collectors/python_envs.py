"""Python environment collector with pip package support."""

import json
import os
import subprocess
from pathlib import Path

from devops.collectors.base import BaseCollector, EnvEntry, Status


class PythonEnvCollector(BaseCollector):
    """Collector for Python environments with pip packages."""

    name = "Python"
    description = "Python installations and virtual environments"

    def collect(self) -> list[EnvEntry]:
        """Collect Python environment information."""
        entries = []

        # System Python
        system_python = self._get_system_python()
        if system_python:
            entries.append(system_python)

        # Homebrew Python
        brew_python = self._get_brew_python()
        if brew_python:
            entries.append(brew_python)

        # Conda environments
        conda_envs = self._get_conda_envs()
        entries.extend(conda_envs)

        # pyenv versions
        pyenv_versions = self._get_pyenv_versions()
        entries.extend(pyenv_versions)

        # virtualenvs in common locations
        venvs = self._find_virtualenvs()
        entries.extend(venvs)

        return entries

    def _run_pip_list(self, python_path: str) -> list[dict]:
        """Run pip list and return package info."""
        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return []

    def _get_system_python(self) -> EnvEntry | None:
        """Get system Python info."""
        python_path = "/usr/bin/python3"
        try:
            result = subprocess.run(
                [python_path, "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip().replace("Python ", "")
                packages = self._run_pip_list(python_path)
                return EnvEntry(
                    name="System Python",
                    path=python_path,
                    status=Status.HEALTHY,
                    details={
                        "version": version,
                        "type": "system",
                        "description": "macOS built-in Python",
                        "packages": packages,
                        "package_count": len(packages),
                        "env_path": python_path,
                        "is_system": True,
                    },
                )
        except Exception:
            pass
        return None

    def _get_brew_python(self) -> EnvEntry | None:
        """Get Homebrew Python info."""
        brew_python = Path("/opt/homebrew/bin/python3")
        if brew_python.exists():
            try:
                result = subprocess.run(
                    [str(brew_python), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    version = result.stdout.strip().replace("Python ", "")
                    packages = self._run_pip_list(str(brew_python))
                    return EnvEntry(
                        name="Homebrew Python",
                        path=str(brew_python),
                        status=Status.HEALTHY,
                        details={
                            "version": version,
                            "type": "homebrew",
                            "description": "Installed via Homebrew",
                            "packages": packages,
                            "package_count": len(packages),
                            "env_path": str(brew_python),
                            "is_system": False,
                        },
                    )
            except Exception:
                pass
        return None

    def _get_conda_envs(self) -> list[EnvEntry]:
        """Get conda environments."""
        entries = []
        try:
            result = subprocess.run(
                ["conda", "env", "list"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.startswith("#") or not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        path = parts[-1]
                        is_active = "*" in line

                        # Get Python version in this env
                        python_path = Path(path) / "bin" / "python"
                        version = ""
                        packages = []
                        if python_path.exists():
                            try:
                                res = subprocess.run(
                                    [str(python_path), "--version"],
                                    capture_output=True,
                                    text=True,
                                    timeout=5,
                                )
                                version = res.stdout.strip().replace("Python ", "")
                                packages = self._run_pip_list(str(python_path))
                            except Exception:
                                pass

                        entries.append(
                            EnvEntry(
                                name=f"conda: {name}"
                                + (" (active)" if is_active else ""),
                                path=path,
                                status=Status.HEALTHY,
                                details={
                                    "version": version,
                                    "type": "conda",
                                    "is_active": is_active,
                                    "env_name": name,
                                    "packages": packages,
                                    "package_count": len(packages),
                                    "env_path": str(python_path),
                                    "is_system": False,
                                },
                            )
                        )
        except Exception:
            pass
        return entries

    def _get_pyenv_versions(self) -> list[EnvEntry]:
        """Get pyenv versions."""
        entries = []
        pyenv_root = Path.home() / ".pyenv" / "versions"
        if pyenv_root.exists():
            for version_dir in pyenv_root.iterdir():
                if version_dir.is_dir():
                    python_path = version_dir / "bin" / "python"
                    if python_path.exists():
                        packages = self._run_pip_list(str(python_path))
                        entries.append(
                            EnvEntry(
                                name=f"pyenv: {version_dir.name}",
                                path=str(version_dir),
                                status=Status.HEALTHY,
                                details={
                                    "version": version_dir.name,
                                    "type": "pyenv",
                                    "packages": packages,
                                    "package_count": len(packages),
                                    "env_path": str(python_path),
                                    "is_system": False,
                                },
                            )
                        )
        return entries

    def _find_virtualenvs(self) -> list[EnvEntry]:
        """Find virtualenvs in common locations."""
        entries = []

        # Check ~/.virtualenvs
        venv_home = Path.home() / ".virtualenvs"
        if venv_home.exists():
            for venv_dir in venv_home.iterdir():
                python_path = venv_dir / "bin" / "python"
                if venv_dir.is_dir() and python_path.exists():
                    packages = self._run_pip_list(str(python_path))
                    entries.append(
                        EnvEntry(
                            name=f"venv: {venv_dir.name}",
                            path=str(venv_dir),
                            status=Status.HEALTHY,
                            details={
                                "type": "virtualenv",
                                "packages": packages,
                                "package_count": len(packages),
                                "env_path": str(python_path),
                                "is_system": False,
                            },
                        )
                    )

        return entries
