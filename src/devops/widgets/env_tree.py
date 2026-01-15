"""Tree widget for displaying environment entries."""

import pyperclip
from rich.text import Text
from textual.message import Message
from textual.widgets import Tree

from devops.collectors.base import EnvEntry, Status


class EnvTree(Tree):
    """Tree widget for displaying environment entries."""

    DEFAULT_CSS = """
    EnvTree {
        height: 100%;
        scrollbar-gutter: stable;
    }
    """

    BINDINGS = [
        ("c", "collapse_all", "Collapse All"),
    ]

    def __init__(self, label: str = "Environment", **kwargs):
        super().__init__(label, **kwargs)
        self._entries: list[EnvEntry] = []
        self.show_root = True
        self.guide_depth = 4
        self.root.allow_expand = False

    def on_mount(self) -> None:
        self.root.expand()
        self.root.allow_expand = False

    def action_collapse_all(self) -> None:
        self.root.collapse_all()
        self.root.expand()
        self.root.allow_expand = False

    def set_entries(self, entries: list[EnvEntry]) -> None:
        self._entries = entries
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        self.clear()

        for entry in self._entries:
            label = self._create_label(entry)
            node = self.root.add(label, data=entry)

            details = entry.details

            # Shell config items
            if "items" in details:
                self._add_shell_config_children(node, entry)
            # PATH entries
            elif "search_order" in details:
                self._add_path_children(node, entry)
            # NPM packages (check before Homebrew to avoid "packages" key collision)
            elif (
                details.get("type") in ("global", "local", "outdated")
                and "packages" in details
                and entry.path in ("npm global", "npm outdated")
            ):
                self._add_npm_children(node, entry)
            # Homebrew packages
            elif "packages" in details and details.get("type") in (
                "outdated",
                "category",
                None,
            ):
                self._add_package_children(
                    node, details["packages"], details.get("type")
                )
            # Symlinks
            elif "symlinks" in details:
                self._add_symlink_children(node, details)
            # Version managers (old style)
            elif "versions" in details and "manager" not in details:
                self._add_version_children(node, details)
            elif "plugins" in details:
                self._add_plugin_children(node, details)
            # Python envs with pip packages
            elif details.get("type") in (
                "conda",
                "pyenv",
                "virtualenv",
                "system",
                "homebrew",
            ):
                self._add_python_children(node, entry)
            # Node.js versions with packages
            elif (
                "manager" in details
                and details.get("packages") is not None
                and "gem_count" not in details
            ):
                self._add_node_children(node, entry)
            # Ruby versions with gems
            elif "gems" in details:
                self._add_ruby_children(node, entry)
            # Rust toolchains with crates
            elif "crates" in details:
                self._add_rust_children(node, entry)
            # asdf plugins with versions
            elif "plugin" in details and "versions" in details:
                self._add_asdf_children(node, entry)
            # Git repositories
            elif "branch" in details:
                self._add_git_children(node, entry)

        self.root.expand()
        self.root.allow_expand = False

    def _add_shell_config_children(self, node, entry: EnvEntry) -> None:
        items = entry.details.get("items", {})
        shell_file = entry.path

        type_icons = {
            "alias": ("Aliases", "cyan"),
            "export": ("Exports", "green"),
            "path": ("PATH modifications", "yellow"),
            "source": ("Sourced files", "magenta"),
            "eval": ("Eval commands", "blue"),
            "function": ("Functions", "white"),
        }

        for item_type, (label, color) in type_icons.items():
            if item_type in items and items[item_type]:
                type_items = items[item_type]
                type_label = Text(f"{label} ({len(type_items)})", style=f"bold {color}")
                type_node = node.add(
                    type_label, data={"type": item_type, "items": type_items}
                )

                for item in type_items:
                    item_text = Text()

                    if item_type == "alias":
                        item_text.append(f"{item.name}", style=f"bold {color}")
                        item_text.append(" → ", style="dim")
                        item_text.append(f"{item.value}")
                    elif item_type == "export":
                        item_text.append(f"{item.name}", style=f"bold {color}")
                        item_text.append(" = ", style="dim")
                        item_text.append(item.value)
                    elif item_type == "path":
                        item_text.append(f"line {item.line_number}: ", style="dim")
                        item_text.append(item.value)
                    elif item_type == "source":
                        item_text.append(f"source ", style="dim")
                        item_text.append(item.value, style=color)
                    elif item_type == "eval":
                        item_text.append(f"eval ", style="dim")
                        item_text.append(item.value, style=color)
                    elif item_type == "function":
                        item_text.append(f"{item.name}()", style=f"bold {color}")
                        item_text.append(" ← click to view", style="dim italic")

                    type_node.add_leaf(
                        item_text,
                        data={
                            "item": item,
                            "type": item_type,
                            "shell_file": shell_file,
                        },
                    )

    def _add_path_children(self, node, entry: EnvEntry) -> None:
        details = entry.details

        if details.get("exists") and details.get("all_executables"):
            execs = details["all_executables"]
            for exe in execs:
                exe_text = Text(f"  {exe}", style="dim")
                node.add_leaf(exe_text, data={"executable": exe, "path": entry.path})

        if details.get("issue"):
            issue = Text(f"⚠ {details['issue']}", style="bold yellow")
            node.add_leaf(issue)
            if details.get("fix_suggestion"):
                fix = Text(f"→ {details['fix_suggestion']}", style="italic yellow")
                node.add_leaf(fix)

    def _add_package_children(self, node, packages: list, pkg_type: str = None) -> None:
        for pkg in packages:
            name = pkg.get("name", str(pkg))
            version = pkg.get("version", "")
            desc = pkg.get("desc", "")

            pkg_text = Text()
            pkg_text.append(f"{name}", style="bold cyan")
            if version:
                pkg_text.append(f" ({version})", style="dim")
            if desc and len(desc) < 50:
                pkg_text.append(f" - {desc}", style="dim italic")

            node.add_leaf(pkg_text, data={"package": pkg})

    def _add_symlink_children(self, node, details: dict) -> None:
        broken = details.get("broken_links", [])
        if broken:
            broken_label = Text(f"Broken ({len(broken)})", style="bold red")
            broken_node = node.add(broken_label, data={"broken_links": broken})
            for link in broken:
                link_text = Text()
                link_text.append(f"✗ {link['name']}", style="red")
                link_text.append(f" → {link['target']}", style="dim")
                broken_node.add_leaf(link_text, data={"symlink": link})

        symlinks = details.get("symlinks", [])
        if symlinks:
            healthy_label = Text(f"Healthy ({len(symlinks)})", style="bold green")
            healthy_node = node.add(healthy_label)
            for link in symlinks[:50]:
                link_text = Text()
                link_text.append(f"✓ {link['name']}", style="green")
                target = (
                    link["target"]
                    .replace("/opt/homebrew/Cellar/", "")
                    .replace("/Users/jrisberg", "~")
                )
                link_text.append(f" → {target}", style="dim")
                healthy_node.add_leaf(link_text, data={"symlink": link})
            if len(symlinks) > 50:
                more = Text(f"... and {len(symlinks) - 50} more", style="dim italic")
                healthy_node.add_leaf(more)

    def _add_version_children(self, node, details: dict) -> None:
        versions = details.get("versions", [])
        current = details.get("current", "")

        for v in versions:
            v_text = Text()
            if v == current or current.endswith(v):
                v_text.append(f"● {v}", style="bold green")
                v_text.append(" (active)", style="dim")
            else:
                v_text.append(f"○ {v}", style="dim")
            node.add_leaf(v_text)

    def _add_plugin_children(self, node, details: dict) -> None:
        plugins = details.get("plugins", [])
        for p in plugins:
            node.add_leaf(Text(f"  {p}", style="cyan"))

    def _add_python_children(self, node, entry: EnvEntry) -> None:
        """Add Python environment children with pip packages."""
        details = entry.details
        env_type = details.get("type", "")
        env_path = details.get("env_path", "")
        is_system = details.get("is_system", False)

        if details.get("version"):
            node.add_leaf(Text(f"  Python {details['version']}", style="cyan"))
        if details.get("is_active"):
            node.add_leaf(Text("  ● Active environment", style="green"))

        # Add pip packages
        packages = details.get("packages", [])
        if packages:
            pkg_label = Text(f"  Packages ({len(packages)})", style="cyan")
            pkg_node = node.add(pkg_label)
            for pkg in packages:
                name = pkg.get("name", "")
                version = pkg.get("version", "")
                pkg_text = Text()
                pkg_text.append(f"    {name}", style="bold")
                if version:
                    pkg_text.append(f" ({version})", style="dim")
                pkg_node.add_leaf(
                    pkg_text,
                    data={
                        "pip_package": pkg,
                        "env_type": env_type,
                        "env_path": env_path,
                        "is_system": is_system,
                    },
                )

    def _add_node_children(self, node, entry: EnvEntry) -> None:
        """Add Node.js version children with global packages."""
        details = entry.details
        manager = details.get("manager", "")
        node_path = details.get("path", "")
        is_current = details.get("is_current", False)

        if is_current:
            node.add_leaf(Text("  ● Current version", style="green"))

        packages = details.get("packages", [])
        if packages:
            pkg_label = Text(f"  Global packages ({len(packages)})", style="cyan")
            pkg_node = node.add(pkg_label)
            for pkg in packages:
                name = pkg.get("name", "")
                version = pkg.get("version", "")
                pkg_text = Text()
                pkg_text.append(f"    {name}", style="bold green")
                if version:
                    pkg_text.append(f" ({version})", style="dim")
                pkg_node.add_leaf(
                    pkg_text,
                    data={
                        "node_package": pkg,
                        "manager": manager,
                        "node_path": node_path,
                    },
                )

    def _add_ruby_children(self, node, entry: EnvEntry) -> None:
        """Add Ruby version children with gems."""
        details = entry.details
        manager = details.get("manager", "")
        ruby_path = details.get("path", "")
        is_current = details.get("is_current", False)

        if is_current:
            node.add_leaf(Text("  ● Current version", style="green"))

        gems = details.get("gems", [])
        if gems:
            gem_label = Text(f"  Gems ({len(gems)})", style="cyan")
            gem_node = node.add(gem_label)
            for gem in gems:
                name = gem.get("name", "")
                version = gem.get("version", "")
                gem_text = Text()
                gem_text.append(f"    {name}", style="bold red")
                if version:
                    gem_text.append(f" ({version})", style="dim")
                gem_node.add_leaf(
                    gem_text,
                    data={
                        "gem": gem,
                        "manager": manager,
                        "ruby_path": ruby_path,
                    },
                )

    def _add_rust_children(self, node, entry: EnvEntry) -> None:
        """Add Rust toolchain children with crates."""
        details = entry.details
        toolchain = details.get("toolchain", "")
        is_default = details.get("is_default", False)

        if is_default:
            node.add_leaf(Text("  ● Default toolchain", style="green"))

        crates = details.get("crates", [])
        if crates:
            crate_label = Text(f"  Installed crates ({len(crates)})", style="cyan")
            crate_node = node.add(crate_label)
            for crate in crates:
                name = crate.get("name", "")
                version = crate.get("version", "")
                crate_text = Text()
                crate_text.append(f"    {name}", style="bold yellow")
                if version:
                    crate_text.append(f" ({version})", style="dim")
                crate_node.add_leaf(
                    crate_text,
                    data={
                        "crate": crate,
                        "toolchain": toolchain,
                    },
                )

    def _add_asdf_children(self, node, entry: EnvEntry) -> None:
        """Add asdf plugin children with versions."""
        details = entry.details
        plugin = details.get("plugin", "")
        versions = details.get("versions", [])

        for ver in versions:
            version_str = ver.get("version", "")
            is_current = ver.get("is_current", False)
            ver_text = Text()
            if is_current:
                ver_text.append(f"  ● {version_str}", style="bold green")
                ver_text.append(" (current)", style="dim")
            else:
                ver_text.append(f"  ○ {version_str}", style="dim")
            node.add_leaf(
                ver_text,
                data={
                    "asdf_version": ver,
                    "plugin": plugin,
                    "is_current": is_current,
                },
            )

    def _add_npm_children(self, node, entry: EnvEntry) -> None:
        """Add NPM package children."""
        details = entry.details
        pkg_type = details.get("type", "global")
        project_path = details.get("project_path", "")
        packages = details.get("packages", [])

        for pkg in packages:
            name = pkg.get("name", "")
            version = pkg.get("version", "")
            pkg_text = Text()
            pkg_text.append(f"  {name}", style="bold green")
            if version:
                pkg_text.append(f" ({version})", style="dim")
            node.add_leaf(
                pkg_text,
                data={
                    "npm_package": pkg,
                    "pkg_type": pkg_type,
                    "project_path": project_path,
                },
            )

    def _add_git_children(self, node, entry: EnvEntry) -> None:
        """Add Git repository status children."""
        details = entry.details

        # Branch info
        branch = details.get("branch", "?")
        branch_text = Text()
        branch_text.append(f"  branch: ", style="dim")
        branch_text.append(branch, style="bold magenta")
        node.add_leaf(branch_text)

        # Status counts
        modified = details.get("modified", 0)
        staged = details.get("staged", 0)
        untracked = details.get("untracked", 0)

        if modified > 0 or staged > 0 or untracked > 0:
            status_text = Text()
            status_text.append("  ", style="dim")
            if staged > 0:
                status_text.append(f"+{staged} staged ", style="green")
            if modified > 0:
                status_text.append(f"~{modified} modified ", style="yellow")
            if untracked > 0:
                status_text.append(f"?{untracked} untracked", style="red")
            node.add_leaf(status_text)

        # Ahead/behind
        ahead = details.get("ahead", 0)
        behind = details.get("behind", 0)
        if ahead > 0 or behind > 0:
            sync_text = Text()
            sync_text.append("  ", style="dim")
            if ahead > 0:
                sync_text.append(f"↑{ahead} ahead ", style="cyan")
            if behind > 0:
                sync_text.append(f"↓{behind} behind", style="yellow")
            node.add_leaf(sync_text)

    def _create_label(self, entry: EnvEntry) -> Text:
        style_map = {
            Status.HEALTHY: "green",
            Status.WARNING: "yellow",
            Status.ERROR: "red",
        }
        icon_map = {
            Status.HEALTHY: "✓",
            Status.WARNING: "⚠",
            Status.ERROR: "✗",
        }

        style = style_map.get(entry.status, "white")
        icon = icon_map.get(entry.status, "?")
        details = entry.details

        text = Text()
        text.append(f"{icon} ", style=style)

        # Shell configs
        if "load_order" in details:
            text.append(f"[{details['load_order']}] ", style="cyan bold")
            text.append(entry.name)
            text.append(f" — {details.get('description', '')}", style="dim italic")
        # PATH entries
        elif "search_order" in details:
            order = details["search_order"]
            total = details["total_paths"]
            text.append(f"[{order}/{total}] ", style="cyan")
            display_path = entry.name.replace("/Users/jrisberg", "~")
            text.append(display_path)
            if details.get("is_homebrew"):
                text.append(" 🍺", style="yellow")
            if details.get("exists") and details.get("executable_count", 0) > 0:
                text.append(f" ({details['executable_count']} cmds)", style="dim")
            if entry.source_file:
                source = entry.source_file.replace("/Users/jrisberg/", "~/")
                text.append(f" ← {source}:{entry.source_line}", style="dim")
        # Homebrew categories
        elif details.get("type") == "category":
            text.append(entry.name)
            text.append(f" ({details.get('count', 0)})", style="dim")
        elif details.get("type") == "outdated":
            text.append(entry.name, style="yellow")
        # Symlinks
        elif "total_symlinks" in details:
            text.append(entry.name.replace("/Users/jrisberg", "~"))
            text.append(f" ({details['total_symlinks']} symlinks", style="dim")
            if details.get("broken", 0) > 0:
                text.append(f", {details['broken']} broken", style="red")
            text.append(")", style="dim")
        # Python envs with package count
        elif details.get("type") in (
            "conda",
            "pyenv",
            "virtualenv",
            "system",
            "homebrew",
        ):
            text.append(entry.name)
            if details.get("version"):
                text.append(f" ({details['version']})", style="dim")
            if details.get("package_count", 0) > 0:
                text.append(f" - {details['package_count']} packages", style="cyan")
        # Node.js versions
        elif (
            "manager" in details
            and "package_count" in details
            and "gem_count" not in details
        ):
            text.append(entry.name)
            if details.get("is_current"):
                text.append(" ●", style="green")
            if details.get("package_count", 0) > 0:
                text.append(f" - {details['package_count']} packages", style="cyan")
        # Ruby versions
        elif "gems" in details or "gem_count" in details:
            text.append(entry.name)
            if details.get("is_current"):
                text.append(" ●", style="green")
            if details.get("gem_count", 0) > 0:
                text.append(f" - {details['gem_count']} gems", style="cyan")
        # Rust toolchains
        elif "crates" in details or "crate_count" in details:
            text.append(entry.name)
            if details.get("is_default"):
                text.append(" ●", style="green")
            if details.get("crate_count", 0) > 0:
                text.append(f" - {details['crate_count']} crates", style="cyan")
        # asdf plugins
        elif "plugin" in details:
            text.append(entry.name)
            if details.get("version_count", 0) > 0:
                text.append(f" ({details['version_count']} versions)", style="dim")
        # NPM groups
        elif details.get("type") in ("global", "local"):
            text.append(entry.name)
            if details.get("package_count", 0) > 0:
                text.append(f" ({details['package_count']})", style="dim")
        # Git repositories
        elif "branch" in details:
            text.append(entry.name)
            branch = details.get("branch", "?")
            text.append(f" [{branch}]", style="magenta")
            if details.get("clean"):
                text.append(" clean", style="dim green")
            else:
                counts = []
                if details.get("staged", 0) > 0:
                    counts.append(f"+{details['staged']}")
                if details.get("modified", 0) > 0:
                    counts.append(f"~{details['modified']}")
                if details.get("untracked", 0) > 0:
                    counts.append(f"?{details['untracked']}")
                if counts:
                    text.append(f" {' '.join(counts)}", style="yellow")
        else:
            text.append(entry.name)

        return text

    def get_selected_entry(self) -> EnvEntry | None:
        node = self.cursor_node
        if node and node.data and isinstance(node.data, EnvEntry):
            return node.data
        if node and node.parent and node.parent.data:
            if isinstance(node.parent.data, EnvEntry):
                return node.parent.data
        return None

    def get_selected_item_data(self) -> dict | None:
        node = self.cursor_node
        if node and node.data and isinstance(node.data, dict):
            return node.data
        return None
