import os
import re
from dataclasses import dataclass
from pathlib import Path

from devops.collectors.base import BaseCollector, EnvEntry, Status


@dataclass
class ConfigItem:
    """An item found in a config file."""

    item_type: str
    name: str
    value: str
    line_number: int
    raw_line: str
    full_body: str = ""


class ShellConfigCollector(BaseCollector):
    """Collector for shell configuration files."""

    name = "Shell Config"
    description = "Shell configuration files and their contents"

    # Config files in loading order for zsh
    CONFIG_FILES = [
        ("~/.zshenv", "Loaded FIRST for all zsh sessions"),
        ("~/.zprofile", "Loaded for LOGIN shells, before .zshrc"),
        ("~/.zshrc", "Loaded for INTERACTIVE shells (main config)"),
        ("~/.zlogin", "Loaded for LOGIN shells, after .zshrc"),
        ("~/.zlogout", "Loaded when LOGIN shell exits"),
    ]

    PATTERNS = {
        "alias": r'^alias\s+([^=]+)=["\']?(.+?)["\']?\s*$',
        "export": r"^export\s+([^=]+)=(.+)$",
        "path": r"(?:export\s+)?PATH\s*=|path\s*\+=",
        "source": r"^(?:source|\.)\s+(.+)$",
        "function": r"^(?:function\s+)?(\w+)\s*\(\)\s*\{",
        "eval": r'^eval\s+"?\$\((.+)\)"?',
    }

    def collect(self) -> list[EnvEntry]:
        """Collect shell config file entries with parsed contents."""
        entries = []
        load_order = 0

        for config_path, description in self.CONFIG_FILES:
            expanded = os.path.expanduser(config_path)
            path_obj = Path(expanded)

            if not path_obj.exists():
                continue

            load_order += 1  # Only increment for files that exist

            try:
                content = path_obj.read_text()
                line_count = len(content.splitlines())
                size = path_obj.stat().st_size

                items = self._parse_config(content)

                grouped = {}
                for item in items:
                    if item.item_type not in grouped:
                        grouped[item.item_type] = []
                    grouped[item.item_type].append(item)

                entry = EnvEntry(
                    name=config_path,
                    path=expanded,
                    status=Status.HEALTHY,
                    details={
                        "load_order": load_order,
                        "description": description,
                        "line_count": line_count,
                        "size_bytes": size,
                        "items": grouped,
                        "item_counts": {k: len(v) for k, v in grouped.items()},
                    },
                )
                entries.append(entry)

            except (PermissionError, UnicodeDecodeError) as e:
                load_order += 1
                entry = EnvEntry(
                    name=config_path,
                    path=expanded,
                    status=Status.ERROR,
                    details={"error": str(e), "load_order": load_order},
                )
                entries.append(entry)

        return entries

    def _parse_config(self, content: str) -> list[ConfigItem]:
        """Parse config file and extract items."""
        items = []
        lines = content.splitlines()
        i = 0

        while i < len(lines):
            line = lines[i]
            line_num = i + 1
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                i += 1
                continue

            # Check for function definitions - capture full body
            func_match = re.match(self.PATTERNS["function"], stripped)
            if func_match:
                func_name = func_match.group(1)
                func_lines = [line]
                brace_count = stripped.count("{") - stripped.count("}")
                j = i + 1
                while j < len(lines) and brace_count > 0:
                    func_lines.append(lines[j])
                    brace_count += lines[j].count("{") - lines[j].count("}")
                    j += 1

                full_body = "\n".join(func_lines)
                items.append(
                    ConfigItem(
                        item_type="function",
                        name=func_name,
                        value="(function)",
                        line_number=line_num,
                        raw_line=stripped,
                        full_body=full_body,
                    )
                )
                i = j
                continue

            # Check for aliases
            alias_match = re.match(self.PATTERNS["alias"], stripped)
            if alias_match:
                items.append(
                    ConfigItem(
                        item_type="alias",
                        name=alias_match.group(1).strip(),
                        value=alias_match.group(2).strip().rstrip("'\""),
                        line_number=line_num,
                        raw_line=stripped,
                    )
                )
                i += 1
                continue

            # Check for PATH modifications
            if re.search(self.PATTERNS["path"], stripped):
                items.append(
                    ConfigItem(
                        item_type="path",
                        name="PATH",
                        value=stripped,
                        line_number=line_num,
                        raw_line=stripped,
                    )
                )
                i += 1
                continue

            # Check for exports
            export_match = re.match(self.PATTERNS["export"], stripped)
            if export_match:
                items.append(
                    ConfigItem(
                        item_type="export",
                        name=export_match.group(1).strip(),
                        value=export_match.group(2).strip().strip("'\""),
                        line_number=line_num,
                        raw_line=stripped,
                    )
                )
                i += 1
                continue

            # Check for source
            source_match = re.match(self.PATTERNS["source"], stripped)
            if source_match:
                items.append(
                    ConfigItem(
                        item_type="source",
                        name="source",
                        value=source_match.group(1).strip(),
                        line_number=line_num,
                        raw_line=stripped,
                    )
                )
                i += 1
                continue

            # Check for eval
            eval_match = re.match(self.PATTERNS["eval"], stripped)
            if eval_match:
                items.append(
                    ConfigItem(
                        item_type="eval",
                        name="eval",
                        value=eval_match.group(1).strip(),
                        line_number=line_num,
                        raw_line=stripped,
                    )
                )
                i += 1
                continue

            i += 1

        return items
