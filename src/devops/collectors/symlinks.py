import os
from pathlib import Path

from devops.collectors.base import BaseCollector, EnvEntry, Status


class SymlinkCollector(BaseCollector):
    """Collector for symlinks in common binary directories."""

    name = "Symlinks"
    description = "Symbolic links in PATH directories"

    # Directories to scan for symlinks
    SCAN_DIRS = [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "~/.local/bin",
    ]

    def collect(self) -> list[EnvEntry]:
        """Collect symlink information."""
        entries = []

        for dir_path in self.SCAN_DIRS:
            expanded = os.path.expanduser(dir_path)
            path_obj = Path(expanded)

            if not path_obj.exists():
                continue

            symlinks = []
            broken = []

            try:
                for item in path_obj.iterdir():
                    if item.is_symlink():
                        target = None
                        is_broken = False
                        try:
                            target = str(item.resolve())
                            if not Path(target).exists():
                                is_broken = True
                        except:
                            is_broken = True

                        link_info = {
                            "name": item.name,
                            "target": target or "(broken)",
                            "broken": is_broken,
                            "full_path": str(item),
                        }

                        if is_broken:
                            broken.append(link_info)
                        else:
                            symlinks.append(link_info)
            except PermissionError:
                continue

            if symlinks or broken:
                status = Status.WARNING if broken else Status.HEALTHY
                entries.append(
                    EnvEntry(
                        name=dir_path,
                        path=expanded,
                        status=status,
                        details={
                            "total_symlinks": len(symlinks) + len(broken),
                            "healthy": len(symlinks),
                            "broken": len(broken),
                            "symlinks": symlinks[:100],  # Limit for performance
                            "broken_links": broken,
                        },
                    )
                )

        return entries
