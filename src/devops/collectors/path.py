import os
import re
from pathlib import Path

from devops.collectors.base import BaseCollector, EnvEntry, Status


class PathCollector(BaseCollector):
    """Collector for PATH environment variable entries."""

    name = "PATH"
    description = "PATH environment variable entries"

    SHELL_CONFIGS = [
        "~/.zshenv",
        "~/.zprofile",
        "~/.zshrc",
        "~/.bashrc",
        "~/.bash_profile",
        "~/.profile",
        "/etc/paths",
        "/etc/paths.d/*",
    ]

    PATH_PATTERNS = [
        r'export\s+PATH\s*=\s*["\']?([^"\'\n]+)["\']?',
        r'PATH\s*=\s*["\']?([^"\'\n]+)["\']?',
        r"path\s*\+=\s*\(([^)]+)\)",
    ]

    # Known special directories
    HOMEBREW_PATHS = ["/opt/homebrew/bin", "/usr/local/bin", "/opt/homebrew/sbin"]

    def collect(self) -> list[EnvEntry]:
        """Collect PATH entries with their sources."""
        entries = []
        path_value = os.environ.get("PATH", "")
        path_dirs = path_value.split(os.pathsep)
        path_sources = self._find_path_sources()
        total_paths = len([p for p in path_dirs if p])

        seen = set()
        order = 0
        for path_dir in path_dirs:
            if not path_dir:
                continue

            order += 1
            path_obj = Path(path_dir)
            status = Status.HEALTHY
            is_duplicate = path_dir in seen
            exists = path_obj.exists()
            is_dir = path_obj.is_dir() if exists else False
            is_symlink = path_obj.is_symlink()

            # Check if this is a Homebrew path
            is_homebrew = path_dir in self.HOMEBREW_PATHS or "/homebrew/" in path_dir

            # Determine issue
            issue = None
            issue_detail = None
            fix_suggestion = None

            if not exists:
                status = Status.ERROR
                issue = "Directory does not exist"
                issue_detail = f"The path '{path_dir}' is in your PATH but doesn't exist. This happens when software is uninstalled but the shell config isn't updated."
                fix_suggestion = "Remove this entry from your shell config file"
            elif is_duplicate:
                status = Status.WARNING
                issue = "Duplicate entry"
                issue_detail = "This path appears multiple times. Only the first occurrence matters."
                fix_suggestion = "Remove the duplicate from your shell config"
            elif not is_dir:
                status = Status.WARNING
                issue = "Not a directory"
                issue_detail = "This path exists but is a file, not a directory."
                fix_suggestion = "Remove this entry or fix the path"

            seen.add(path_dir)

            # Get source info
            source_file = None
            source_line = None
            if path_dir in path_sources:
                source_file, source_line = path_sources[path_dir]

            # Resolve symlink
            real_path = None
            if is_symlink:
                try:
                    real_path = str(path_obj.resolve())
                except:
                    pass

            # Get ALL executables (for browsing)
            exec_count = 0
            all_executables = []
            if exists and is_dir:
                try:
                    execs = sorted(
                        [
                            f.name
                            for f in path_obj.iterdir()
                            if f.is_file() and os.access(f, os.X_OK)
                        ]
                    )
                    exec_count = len(execs)
                    all_executables = execs
                except PermissionError:
                    pass

            entry = EnvEntry(
                name=path_dir,
                path=path_dir,
                status=status,
                source_file=source_file,
                source_line=source_line,
                details={
                    "search_order": order,
                    "total_paths": total_paths,
                    "exists": exists,
                    "is_directory": is_dir,
                    "is_symlink": is_symlink,
                    "real_path": real_path,
                    "is_duplicate": is_duplicate,
                    "is_homebrew": is_homebrew,
                    "executable_count": exec_count,
                    "all_executables": all_executables,
                    "issue": issue,
                    "issue_detail": issue_detail,
                    "fix_suggestion": fix_suggestion,
                },
            )
            entries.append(entry)

        return entries

    def _find_path_sources(self) -> dict[str, tuple[str, int]]:
        """Find where each PATH entry is defined."""
        sources: dict[str, tuple[str, int]] = {}

        for config_pattern in self.SHELL_CONFIGS:
            expanded = os.path.expanduser(config_pattern)

            if "*" in expanded:
                config_paths = list(Path(expanded).parent.glob(Path(expanded).name))
            else:
                config_paths = [Path(expanded)]

            for config_path in config_paths:
                if not config_path.exists() or not config_path.is_file():
                    continue

                try:
                    file_content = config_path.read_text()
                    for line_num, line in enumerate(file_content.splitlines(), 1):
                        if line.strip().startswith("#"):
                            continue

                        for pattern in self.PATH_PATTERNS:
                            match = re.search(pattern, line)
                            if match:
                                path_str = match.group(1)
                                for part in path_str.split(":"):
                                    part = part.strip()
                                    if part and not part.startswith("$"):
                                        expanded_part = os.path.expanduser(
                                            os.path.expandvars(part)
                                        )
                                        if expanded_part not in sources:
                                            sources[expanded_part] = (
                                                str(config_path),
                                                line_num,
                                            )
                except (PermissionError, UnicodeDecodeError):
                    continue

        return sources
