"""Rust toolchain collector for rustup."""

import os
import subprocess
from pathlib import Path

from devops.collectors.base import BaseCollector, EnvEntry, Status


class RustCollector(BaseCollector):
    """Collects Rust toolchains from rustup."""

    @staticmethod
    def is_available() -> bool:
        """Check if rustup has installed toolchains.

        Only uses fast filesystem checks - no subprocess calls.
        """
        rustup_home = os.environ.get("RUSTUP_HOME", str(Path.home() / ".rustup"))
        toolchains_dir = Path(rustup_home) / "toolchains"
        try:
            if toolchains_dir.exists() and any(toolchains_dir.iterdir()):
                return True
        except (PermissionError, OSError):
            pass

        return False

    def collect(self) -> list[EnvEntry]:
        """Collect all Rust toolchains."""
        entries = []

        try:
            # Get list of installed toolchains
            result = subprocess.run(
                ["rustup", "toolchain", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return entries

            # Get default toolchain
            default = ""
            default_result = subprocess.run(
                ["rustup", "default"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if default_result.returncode == 0:
                default = (
                    default_result.stdout.split()[0] if default_result.stdout else ""
                )

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                toolchain = line.strip()
                is_default = "(default)" in toolchain or toolchain == default
                toolchain_name = toolchain.replace(" (default)", "").strip()

                # Get installed crates for this toolchain
                crates = self._get_crates(toolchain_name)

                # Determine toolchain type for styling
                if "stable" in toolchain_name:
                    status = Status.HEALTHY
                elif "beta" in toolchain_name:
                    status = Status.WARNING
                else:  # nightly
                    status = Status.HEALTHY

                entries.append(
                    EnvEntry(
                        name=f"Rust {toolchain_name}",
                        status=status,
                        details={
                            "toolchain": toolchain_name,
                            "is_default": is_default,
                            "crates": crates,
                            "crate_count": len(crates),
                        },
                    )
                )

        except Exception:
            pass

        return entries

    def _get_crates(self, toolchain: str) -> list[dict]:
        """Get installed crates for a toolchain."""
        crates = []

        # Get cargo home
        cargo_home = os.environ.get("CARGO_HOME", str(Path.home() / ".cargo"))
        bin_dir = Path(cargo_home) / "bin"

        if not bin_dir.exists():
            return crates

        # List binaries in cargo bin (these are the installed crates)
        try:
            for binary in bin_dir.iterdir():
                if binary.is_file() and not binary.name.startswith("."):
                    # Skip rustup-managed binaries
                    if binary.name in [
                        "rustup",
                        "cargo",
                        "rustc",
                        "rustfmt",
                        "clippy-driver",
                        "cargo-fmt",
                        "cargo-clippy",
                        "rust-gdb",
                        "rust-lldb",
                        "rustdoc",
                    ]:
                        continue
                    crates.append(
                        {
                            "name": binary.name,
                            "version": "",  # Would need to run binary --version to get this
                        }
                    )
        except Exception:
            pass

        return crates
