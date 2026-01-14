"""Detail panel widget for showing entry details."""

import subprocess

from rich.text import Text
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widgets import Button, Input, Static

from devops.cache.brew_cache import get_brew_cache
from devops.collectors.base import EnvEntry, Status


class DetailPanel(VerticalScroll):
    """Panel showing details of the selected entry."""

    # Homebrew messages
    class UpgradePackage(Message):
        def __init__(self, package_name: str) -> None:
            self.package_name = package_name
            super().__init__()

    class BrewUpdate(Message):
        pass

    class BrewUpgradeAll(Message):
        pass

    class BrewUninstallPackage(Message):
        def __init__(self, package_name: str):
            self.package_name = package_name
            super().__init__()

    # Symlink messages
    class DeleteSymlink(Message):
        def __init__(self, symlink_path: str) -> None:
            self.symlink_path = symlink_path
            super().__init__()

    class DeleteAllBroken(Message):
        def __init__(self, symlink_paths: list) -> None:
            self.symlink_paths = symlink_paths
            super().__init__()

    class SudoDelete(Message):
        def __init__(self, path: str, password: str) -> None:
            self.path = path
            self.password = password
            super().__init__()

    class SudoDeleteAll(Message):
        def __init__(self, paths: list, password: str) -> None:
            self.paths = paths
            self.password = password
            super().__init__()

    # PIP messages
    class UninstallPipPackage(Message):
        def __init__(self, package_name: str, env_path: str, is_system: bool) -> None:
            self.package_name = package_name
            self.env_path = env_path
            self.is_system = is_system
            super().__init__()

    # NPM messages
    class UninstallNpmPackage(Message):
        def __init__(
            self, package_name: str, is_global: bool, project_path: str = ""
        ) -> None:
            self.package_name = package_name
            self.is_global = is_global
            self.project_path = project_path
            super().__init__()

    class NpmUpgradeAll(Message):
        pass

    class NpmUpgradePackage(Message):
        def __init__(self, package_name: str):
            self.package_name = package_name
            super().__init__()

    # Shell config editing messages
    class SaveAlias(Message):
        def __init__(
            self,
            file_path: str,
            name: str,
            value: str,
            old_name: str = "",
            line_number: int = 0,
        ) -> None:
            self.file_path = file_path
            self.name = name
            self.value = value
            self.old_name = old_name
            self.line_number = line_number
            super().__init__()

    class DeleteAlias(Message):
        def __init__(self, file_path: str, name: str, line_number: int) -> None:
            self.file_path = file_path
            self.name = name
            self.line_number = line_number
            super().__init__()

    class SaveFunction(Message):
        def __init__(
            self,
            file_path: str,
            name: str,
            body: str,
            start_line: int = 0,
            end_line: int = 0,
        ) -> None:
            self.file_path = file_path
            self.name = name
            self.body = body
            self.start_line = start_line
            self.end_line = end_line
            super().__init__()

    class DeleteFunction(Message):
        def __init__(
            self, file_path: str, name: str, start_line: int, end_line: int
        ) -> None:
            self.file_path = file_path
            self.name = name
            self.start_line = start_line
            self.end_line = end_line
            super().__init__()

    DEFAULT_CSS = """
    DetailPanel {
        height: 100%;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
    }

    DetailPanel > Button {
        margin-top: 1;
        width: auto;
    }

    DetailPanel > Input {
        margin-top: 1;
        width: 100%;
    }

    DetailPanel > .form-label {
        margin-top: 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._content = Static(self._get_welcome_text())
        self._shown_welcome = False
        self._current_package = None
        self._current_symlink = None
        self._all_broken_symlinks = []
        self._awaiting_password = False
        self._password_action = None
        # PIP/NPM state
        self._current_pip_package = None
        self._current_npm_package = None
        # Shell editing state
        self._editing_alias = False
        self._editing_function = False
        self._current_shell_file = None
        self._current_alias_item = None
        self._current_function_item = None

    def compose(self):
        yield self._content

    def _get_welcome_text(self) -> Text:
        text = Text()
        text.append("devops\n", style="bold underline cyan")
        text.append("Development Environment Topology\n\n", style="dim italic")
        text.append("Navigate the tree to explore your environment.\n\n")
        text.append("Tips:\n", style="bold")
        text.append("- Press ", style="dim")
        text.append("c", style="bold cyan")
        text.append(" to collapse all\n", style="dim")
        text.append("- Press ", style="dim")
        text.append("r", style="bold cyan")
        text.append(" to refresh data\n", style="dim")
        text.append("- Press ", style="dim")
        text.append("q", style="bold cyan")
        text.append(" to quit\n", style="dim")
        return text

    def _clear_buttons(self):
        """Remove any existing buttons, inputs, and form labels."""
        for btn in list(self.query(Button)):
            btn.remove()
        for inp in list(self.query(Input)):
            inp.remove()
        for widget in list(self.query(".form-label")):
            widget.remove()
        self._awaiting_password = False

    # Welcome pages
    def show_path_welcome(self) -> None:
        self._clear_buttons()
        content = Text()
        content.append("PATH Search Order\n\n", style="bold cyan underline")
        content.append("How PATH Works:\n", style="bold")
        content.append(
            "When you type a command, your shell searches directories\n", style="dim"
        )
        content.append(
            "in order until it finds a matching executable.\n\n", style="dim"
        )
        content.append("Earlier entries take priority over later ones.\n", style="dim")
        content.append("Click a PATH entry to see its commands.\n", style="italic")
        self._content.update(content)
        self._shown_welcome = True

    def show_shell_welcome(self) -> None:
        self._clear_buttons()
        content = Text()
        content.append("Shell Configuration\n\n", style="bold cyan underline")
        content.append("Load Order:\n", style="bold")
        content.append("1. ~/.zshenv    - Always loaded first\n", style="dim")
        content.append("2. ~/.zprofile  - Login shells only\n", style="dim")
        content.append("3. ~/.zshrc     - Interactive shells\n\n", style="dim")
        content.append("Click a config file to see its aliases,\n", style="italic")
        content.append("exports, functions, and sourced files.\n", style="italic")
        self._content.update(content)
        self._shown_welcome = True

    def show_homebrew_welcome(
        self, outdated_count: int = 0, loading: bool = False, syncing: bool = False
    ) -> None:
        self._clear_buttons()
        content = Text()
        content.append("Homebrew Packages\n\n", style="bold cyan underline")
        content.append("Manage your Homebrew formulae and casks.\n\n", style="dim")

        if loading:
            content.append("Status: ", style="bold")
            content.append("Loading package information...\n\n", style="dim italic")
        elif syncing:
            content.append("Status: ", style="bold")
            content.append("Syncing with Homebrew...\n\n", style="cyan italic")
            if outdated_count > 0:
                content.append("Outdated: ", style="bold")
                content.append(
                    f"{outdated_count} packages need updates\n\n", style="yellow"
                )
        elif outdated_count > 0:
            content.append("Outdated: ", style="bold")
            content.append(
                f"{outdated_count} packages need updates\n\n", style="yellow"
            )
        else:
            content.append("Status: ", style="bold")
            content.append("All packages up to date!\n\n", style="green")

        content.append(
            "Click a package for details and upgrade options.\n", style="italic"
        )
        self._content.update(content)
        self._shown_welcome = True

        import time

        ts = int(time.time() * 1000)
        self.mount(
            Button("Check for Updates", id=f"brew-update-{ts}", variant="primary")
        )
        if outdated_count > 0:
            self.mount(
                Button(
                    f"Upgrade All ({outdated_count})",
                    id=f"brew-upgrade-all-{ts}",
                    variant="success",
                )
            )

    def show_symlinks_welcome(self, broken_count: int = 0) -> None:
        self._clear_buttons()
        content = Text()
        content.append("Symlinks\n\n", style="bold cyan underline")
        content.append("Symbolic links in your PATH directories.\n\n", style="dim")
        if broken_count > 0:
            content.append("Broken: ", style="bold")
            content.append(f"{broken_count} broken symlinks found\n\n", style="red")
        content.append(
            "Click on Broken to see and delete broken links.\n", style="italic"
        )
        self._content.update(content)
        self._shown_welcome = True

    def show_python_welcome(self, detected: list = None) -> None:
        self._clear_buttons()
        content = Text()
        content.append("Python Environments\n\n", style="bold cyan underline")
        content.append(
            "Your Python installations and virtual environments.\n\n", style="dim"
        )
        if detected:
            content.append("Detected:\n", style="bold")
            for src in detected:
                content.append(f"  - {src}\n", style="green")
            content.append("\n")
        content.append("Click an environment to see its packages.\n", style="italic")
        self._content.update(content)
        self._shown_welcome = True

    def show_node_welcome(self, manager: str = "unknown") -> None:
        self._clear_buttons()
        content = Text()
        content.append("Node.js Environments\n\n", style="bold cyan underline")
        content.append(
            "Your Node.js installations and global packages.\n\n", style="dim"
        )
        manager_names = {
            "nvm": "nvm",
            "fnm": "fnm",
            "volta": "Volta",
            "homebrew": "Homebrew",
            "system": "System",
        }
        if manager and manager != "unknown":
            content.append("Managed by: ", style="bold")
            content.append(f"{manager_names.get(manager, manager)}\n\n", style="green")
        content.append("Click a version to see its global packages.\n", style="italic")
        self._content.update(content)
        self._shown_welcome = True

    def show_ruby_welcome(self, manager: str = "unknown") -> None:
        self._clear_buttons()
        content = Text()
        content.append("Ruby Environments\n\n", style="bold cyan underline")
        content.append("Your Ruby installations and gems.\n\n", style="dim")
        manager_names = {
            "rbenv": "rbenv",
            "chruby": "chruby",
            "homebrew": "Homebrew",
            "system": "System Ruby",
        }
        if manager and manager != "unknown":
            content.append("Managed by: ", style="bold")
            content.append(f"{manager_names.get(manager, manager)}\n\n", style="green")
        content.append("Click a version to see its installed gems.\n", style="italic")
        self._content.update(content)
        self._shown_welcome = True

    def show_rust_welcome(self) -> None:
        self._clear_buttons()
        content = Text()
        content.append("Rust Toolchains\n\n", style="bold cyan underline")
        content.append("Your Rust toolchains managed by rustup.\n\n", style="dim")
        content.append("Toolchain Types:\n", style="bold")
        content.append("  - ", style="dim")
        content.append("stable", style="green")
        content.append(": Production-ready releases\n", style="dim")
        content.append("  - ", style="dim")
        content.append("beta", style="yellow")
        content.append(": Pre-release testing\n", style="dim")
        content.append("  - ", style="dim")
        content.append("nightly", style="magenta")
        content.append(": Latest development features\n\n", style="dim")
        content.append("Click a toolchain to see installed crates.\n", style="italic")
        self._content.update(content)
        self._shown_welcome = True

    def show_asdf_welcome(self, plugins: list = None) -> None:
        self._clear_buttons()
        content = Text()
        content.append("asdf Version Manager\n\n", style="bold cyan underline")
        content.append("Manage multiple runtime versions with asdf.\n\n", style="dim")
        if plugins:
            content.append("Installed Plugins:\n", style="bold")
            for plugin in plugins:
                content.append(f"  - {plugin}\n", style="green")
            content.append("\n")
        content.append(
            "Click a plugin to see its installed versions.\n", style="italic"
        )
        self._content.update(content)
        self._shown_welcome = True

    def show_npm_welcome(
        self, has_global: bool = False, has_local: bool = False
    ) -> None:
        self._clear_buttons()
        content = Text()
        content.append("NPM Packages\n\n", style="bold cyan underline")
        content.append("Node.js packages installed via npm.\n\n", style="dim")
        content.append("Click a package to see details.\n", style="italic")
        self._content.update(content)
        self._shown_welcome = True

    def show_npm_outdated_summary(self, packages: list) -> None:
        """Show NPM outdated packages summary with upgrade button."""
        self._clear_buttons()
        content = Text()
        content.append(
            f"Outdated NPM Packages ({len(packages)})\n\n",
            style="bold yellow underline",
        )
        content.append("These global packages have updates available:\n\n", style="dim")

        for pkg in packages[:15]:
            name = pkg.get("name", "?")
            current = pkg.get("current", "?")
            latest = pkg.get("latest", "?")
            content.append(f"  {name}\n", style="bold")
            content.append(f"    {current}", style="yellow")
            content.append(" -> ", style="dim")
            content.append(f"{latest}\n", style="green")

        if len(packages) > 15:
            content.append(
                f"\n  ... and {len(packages) - 15} more\n", style="dim italic"
            )

        self._content.update(content)
        self._shown_welcome = True

        if packages:
            import time

            self.mount(
                Button(
                    f"Upgrade All ({len(packages)})",
                    id=f"npm-upgrade-all-{int(time.time() * 1000)}",
                    variant="success",
                )
            )

    # Package display methods
    def show_pip_package(
        self, pkg: dict, env_type: str, env_path: str, is_system: bool
    ) -> None:
        self._clear_buttons()
        name = pkg.get("name", "Unknown")
        version = pkg.get("version", "")
        self._current_pip_package = {
            "name": name,
            "env_path": env_path,
            "is_system": is_system,
        }

        content = Text()
        content.append(f"{name}\n", style="bold cyan underline")
        if version:
            content.append("\nVersion: ", style="bold")
            content.append(f"{version}\n", style="white")
        content.append("\nEnvironment: ", style="bold")
        content.append(f"{env_type}\n", style="white")
        if env_path:
            content.append("Path: ", style="bold")
            content.append(f"{env_path}\n", style="dim")
        if is_system:
            content.append("\n", style="")
            content.append("WARNING: ", style="bold yellow")
            content.append("This is a system Python package.\n", style="yellow")
            content.append(
                "Uninstalling may require --break-system-packages\n", style="yellow"
            )

        self._content.update(content)
        self._shown_welcome = True

        import time

        variant = "warning" if is_system else "error"
        self.mount(
            Button(
                f"Uninstall {name}",
                id=f"pip-uninstall-{int(time.time() * 1000)}",
                variant=variant,
            )
        )

    def show_npm_package(
        self, pkg: dict, pkg_type: str, project_path: str = ""
    ) -> None:
        self._clear_buttons()
        name = pkg.get("name", "Unknown")
        version = pkg.get("version", "")
        current = pkg.get("current", "")
        latest = pkg.get("latest", "")
        is_global = pkg_type in ("global", "outdated")  # outdated are global packages
        is_outdated = bool(current and latest)

        self._current_npm_package = {
            "name": name,
            "is_global": is_global,
            "project_path": project_path,
        }

        content = Text()
        content.append(f"{name}\n", style="bold green underline")

        if is_outdated:
            content.append("\nInstalled: ", style="bold")
            content.append(f"{current}\n", style="yellow")
            content.append("Available: ", style="bold")
            content.append(f"{latest}\n", style="green")
        elif version:
            content.append("\nVersion: ", style="bold")
            content.append(f"{version}\n", style="white")

        content.append("\nScope: ", style="bold")
        content.append(
            "Global\n" if is_global else "Local\n",
            style="cyan" if is_global else "magenta",
        )
        if project_path:
            content.append("Project: ", style="bold")
            content.append(f"{project_path}\n", style="dim")

        self._content.update(content)
        self._shown_welcome = True

        import time

        if is_outdated and is_global:
            self.mount(
                Button(
                    f"Upgrade {name}",
                    id=f"npm-upgrade-{int(time.time() * 1000)}",
                    variant="success",
                )
            )

        self.mount(
            Button(
                f"Uninstall {name}",
                id=f"npm-uninstall-{int(time.time() * 1000)}",
                variant="error",
            )
        )

    def show_node_package(self, pkg: dict, manager: str, node_path: str = "") -> None:
        self._clear_buttons()
        name = pkg.get("name", "Unknown")
        version = pkg.get("version", "")

        content = Text()
        content.append(f"{name}\n", style="bold green underline")
        if version:
            content.append("\nVersion: ", style="bold")
            content.append(f"{version}\n", style="white")
        content.append("\nManager: ", style="bold")
        content.append(f"{manager}\n", style="cyan")
        if node_path:
            content.append("Node path: ", style="bold")
            content.append(f"{node_path}\n", style="dim")

        self._content.update(content)
        self._shown_welcome = True

    def show_gem_package(self, pkg: dict, manager: str, ruby_path: str = "") -> None:
        self._clear_buttons()
        name = pkg.get("name", "Unknown")
        version = pkg.get("version", "")

        content = Text()
        content.append(f"{name}\n", style="bold red underline")
        if version:
            content.append("\nVersion: ", style="bold")
            content.append(f"{version}\n", style="white")
        content.append("\nManager: ", style="bold")
        content.append(f"{manager}\n", style="cyan")
        if ruby_path:
            content.append("Ruby path: ", style="bold")
            content.append(f"{ruby_path}\n", style="dim")

        self._content.update(content)
        self._shown_welcome = True

    def show_cargo_package(self, pkg: dict, toolchain: str = "") -> None:
        self._clear_buttons()
        name = pkg.get("name", "Unknown")
        version = pkg.get("version", "")

        content = Text()
        content.append(f"{name}\n", style="bold yellow underline")
        if version:
            content.append("\nVersion: ", style="bold")
            content.append(f"{version}\n", style="white")
        if toolchain:
            content.append("\nToolchain: ", style="bold")
            content.append(f"{toolchain}\n", style="cyan")
        content.append("\nInstalled via: ", style="bold")
        content.append("cargo install\n", style="dim")

        self._content.update(content)
        self._shown_welcome = True

    def show_asdf_version(
        self, version: dict, plugin: str, is_current: bool = False
    ) -> None:
        self._clear_buttons()
        ver = version.get("version", "Unknown")

        content = Text()
        content.append(f"{plugin} {ver}\n", style="bold cyan underline")
        content.append("\nStatus: ", style="bold")
        if is_current:
            content.append("Current version\n", style="green")
        else:
            content.append("Installed\n", style="dim")
        content.append("\nManaged by: ", style="bold")
        content.append("asdf\n", style="magenta")

        self._content.update(content)
        self._shown_welcome = True

    # Shell config editing
    def show_shell_file_selected(self, file_path: str, file_name: str) -> None:
        self._clear_buttons()
        self._current_shell_file = file_path
        self._current_alias_item = None
        self._current_function_item = None

        content = Text()
        content.append(f"{file_name}\n\n", style="bold cyan underline")
        content.append("Shell configuration file.\n\n", style="dim")
        content.append("Select an alias or function to edit,\n", style="italic")
        content.append("or add a new one below.\n", style="italic")

        self._content.update(content)
        self._shown_welcome = True

        import time

        ts = int(time.time() * 1000)
        self.mount(Button("Add Alias", id=f"add-alias-{ts}", variant="success"))
        self.mount(Button("Add Function", id=f"add-function-{ts}", variant="success"))

    def show_alias(self, item, shell_file: str = None) -> None:
        self._clear_buttons()
        self._current_alias_item = item
        if shell_file:
            self._current_shell_file = shell_file

        if hasattr(item, "name"):
            name, value, line_num = item.name, item.value, item.line_number
        else:
            name, value, line_num = (
                item.get("name", ""),
                item.get("value", ""),
                item.get("line_number", "?"),
            )

        content = Text()
        content.append(f"Alias: {name}\n\n", style="bold cyan underline")
        content.append("Expands to:\n", style="bold")
        content.append(f"{value}\n\n", style="white on dark_blue")
        content.append(f"Defined at line {line_num}\n", style="dim")
        content.append("\n[Copied to clipboard]", style="green italic")

        self._content.update(content)
        self._shown_welcome = True

        if self._current_shell_file:
            import time

            ts = int(time.time() * 1000)
            self.mount(Button("Edit", id=f"edit-alias-{ts}", variant="primary"))
            self.mount(Button("Delete", id=f"delete-alias-{ts}", variant="error"))

    def show_function(self, item, shell_file: str = None) -> None:
        self._clear_buttons()
        self._current_function_item = item
        if shell_file:
            self._current_shell_file = shell_file

        if hasattr(item, "name"):
            name, line_num, body = item.name, item.line_number, item.full_body
        else:
            name, line_num, body = (
                item.get("name", ""),
                item.get("line_number", "?"),
                item.get("full_body", ""),
            )

        content = Text()
        content.append(f"Function: {name}()\n\n", style="bold cyan underline")
        content.append(f"Defined at line {line_num}\n\n", style="dim")
        content.append("Code:\n", style="bold")
        content.append("-" * 40 + "\n", style="dim")
        content.append(body, style="white on dark_blue")
        content.append("\n" + "-" * 40, style="dim")

        self._content.update(content)
        self._shown_welcome = True

        if self._current_shell_file:
            import time

            ts = int(time.time() * 1000)
            self.mount(Button("Edit", id=f"edit-function-{ts}", variant="primary"))
            self.mount(Button("Delete", id=f"delete-function-{ts}", variant="error"))

    def _show_edit_alias_form(self) -> None:
        self._clear_buttons()
        self._editing_alias = True
        item = self._current_alias_item
        if not item:
            return

        if hasattr(item, "name"):
            name, value = item.name, item.value
        else:
            name, value = item.get("name", ""), item.get("value", "")

        content = Text()
        content.append("Edit Alias\n\n", style="bold cyan underline")
        self._content.update(content)

        import time

        ts = int(time.time() * 1000)
        self.mount(Static("Name:", classes="form-label"))
        self.mount(Input(value=name, placeholder="Alias name", id=f"alias-name-{ts}"))
        self.mount(Static("Command:", classes="form-label"))
        self.mount(Input(value=value, placeholder="Command", id=f"alias-value-{ts}"))
        self.mount(Button("Save", id=f"save-alias-{ts}", variant="success"))
        self.mount(Button("Cancel", id=f"cancel-edit-{ts}", variant="default"))

    def _show_add_alias_form(self) -> None:
        self._clear_buttons()
        self._editing_alias = True
        self._current_alias_item = None

        content = Text()
        content.append("Add New Alias\n\n", style="bold green underline")
        self._content.update(content)

        import time

        ts = int(time.time() * 1000)
        self.mount(Static("Name:", classes="form-label"))
        self.mount(Input(placeholder="Alias name (e.g., ll)", id=f"alias-name-{ts}"))
        self.mount(Static("Command:", classes="form-label"))
        self.mount(Input(placeholder="Command (e.g., ls -la)", id=f"alias-value-{ts}"))
        self.mount(Button("Save", id=f"save-alias-{ts}", variant="success"))
        self.mount(Button("Cancel", id=f"cancel-edit-{ts}", variant="default"))

    def _show_edit_function_form(self) -> None:
        self._clear_buttons()
        self._editing_function = True
        item = self._current_function_item
        if not item:
            return

        if hasattr(item, "name"):
            name, body = item.name, item.full_body
        else:
            name, body = item.get("name", ""), item.get("full_body", "")

        content = Text()
        content.append("Edit Function\n\n", style="bold cyan underline")
        self._content.update(content)

        import time

        ts = int(time.time() * 1000)
        self.mount(Static("Name:", classes="form-label"))
        self.mount(Input(value=name, placeholder="Function name", id=f"func-name-{ts}"))
        self.mount(Static("Body (full function):", classes="form-label"))
        self.mount(Input(value=body, placeholder="Function body", id=f"func-body-{ts}"))
        self.mount(Button("Save", id=f"save-function-{ts}", variant="success"))
        self.mount(Button("Cancel", id=f"cancel-edit-{ts}", variant="default"))

    def _show_add_function_form(self) -> None:
        self._clear_buttons()
        self._editing_function = True
        self._current_function_item = None

        content = Text()
        content.append("Add New Function\n\n", style="bold green underline")
        self._content.update(content)

        import time

        ts = int(time.time() * 1000)
        self.mount(Static("Name:", classes="form-label"))
        self.mount(
            Input(placeholder="Function name (e.g., myhelper)", id=f"func-name-{ts}")
        )
        self.mount(Static("Body (just the commands):", classes="form-label"))
        self.mount(Input(placeholder="Function body (commands)", id=f"func-body-{ts}"))
        self.mount(Button("Save", id=f"save-function-{ts}", variant="success"))
        self.mount(Button("Cancel", id=f"cancel-edit-{ts}", variant="default"))

    def _save_alias_from_form(self) -> None:
        inputs = list(self.query(Input))
        name_input = value_input = None
        for inp in inputs:
            if inp.id and "alias-name" in inp.id:
                name_input = inp
            elif inp.id and "alias-value" in inp.id:
                value_input = inp

        if not name_input or not value_input:
            return

        name = name_input.value.strip()
        value = value_input.value.strip()

        if not name or not value:
            self.app.notify("Name and command are required", severity="error")
            return

        old_name = ""
        line_number = 0
        if self._current_alias_item:
            if hasattr(self._current_alias_item, "name"):
                old_name = self._current_alias_item.name
                line_number = self._current_alias_item.line_number
            else:
                old_name = self._current_alias_item.get("name", "")
                line_number = self._current_alias_item.get("line_number", 0)

        self.post_message(
            self.SaveAlias(self._current_shell_file, name, value, old_name, line_number)
        )
        self._editing_alias = False

    def _save_function_from_form(self) -> None:
        inputs = list(self.query(Input))
        name_input = body_input = None
        for inp in inputs:
            if inp.id and "func-name" in inp.id:
                name_input = inp
            elif inp.id and "func-body" in inp.id:
                body_input = inp

        if not name_input or not body_input:
            return

        name = name_input.value.strip()
        body = body_input.value.strip()

        if not name or not body:
            self.app.notify("Name and body are required", severity="error")
            return

        start_line = end_line = 0
        if self._current_function_item:
            if hasattr(self._current_function_item, "line_number"):
                start_line = self._current_function_item.line_number
                end_line = getattr(self._current_function_item, "end_line", start_line)
            else:
                start_line = self._current_function_item.get("line_number", 0)
                end_line = self._current_function_item.get("end_line", start_line)

        self.post_message(
            self.SaveFunction(
                self._current_shell_file, name, body, start_line, end_line
            )
        )
        self._editing_function = False

    # Homebrew display
    def show_outdated_summary(self, packages: list) -> None:
        self._clear_buttons()
        content = Text()
        content.append(
            f"Outdated Packages ({len(packages)})\n\n", style="bold yellow underline"
        )
        content.append("These packages have updates available:\n\n", style="dim")

        for pkg in packages[:15]:
            name = pkg.get("name", "?")
            current = pkg.get("current", "?")
            latest = pkg.get("latest", "?")
            content.append(f"  {name}\n", style="bold")
            content.append(f"    {current}", style="yellow")
            content.append(" -> ", style="dim")
            content.append(f"{latest}\n", style="green")

        if len(packages) > 15:
            content.append(
                f"\n  ... and {len(packages) - 15} more\n", style="dim italic"
            )

        self._content.update(content)
        self._shown_welcome = True

        if packages:
            import time

            self.mount(
                Button(
                    f"Upgrade All ({len(packages)})",
                    id=f"brew-upgrade-all-{int(time.time() * 1000)}",
                    variant="success",
                )
            )

    def show_package(self, pkg: dict) -> None:
        self._clear_buttons()
        name = pkg.get("name", "Unknown")
        version = pkg.get("version", "")
        desc = pkg.get("desc", "")
        homepage = pkg.get("homepage", "")
        current = pkg.get("current", "")
        latest = pkg.get("latest", "")

        is_outdated = bool(current and latest)
        self._current_package = name

        content = Text()
        content.append(f"{name}\n", style="bold cyan underline")

        if version:
            content.append("\nVersion: ", style="bold")
            content.append(f"{version}\n", style="white")

        if is_outdated:
            content.append("\nInstalled: ", style="bold")
            content.append(f"{current}\n", style="yellow")
            content.append("Available: ", style="bold")
            content.append(f"{latest}\n", style="green")

        if desc:
            content.append("\nDescription:\n", style="bold")
            content.append(f"{desc}\n", style="white")

        if homepage:
            content.append("\nHomepage: ", style="bold")
            content.append(f"{homepage}\n", style="blue underline")

        cache = get_brew_cache()
        cached_info = cache.get(name)
        if cached_info:
            content.append("\nBrew Info:\n", style="bold")
            content.append("-" * 40 + "\n", style="dim")
            content.append(cached_info, style="dim")
        else:
            content.append("\nLoading brew info...\n", style="dim italic")

        self._content.update(content)
        self._shown_welcome = True

        import time

        if is_outdated:
            self.mount(
                Button(
                    f"Upgrade {name}",
                    id=f"upgrade-btn-{int(time.time() * 1000)}",
                    variant="success",
                )
            )

        self.mount(
            Button(
                f"Uninstall {name}",
                id=f"brew-uninstall-{int(time.time() * 1000)}",
                variant="error",
            )
        )

        if not cache.has(name):
            self.set_timer(0.05, lambda: self._load_brew_info(pkg))

    def _load_brew_info(self, pkg: dict) -> None:
        name = pkg.get("name", "Unknown")
        version = pkg.get("version", "")
        desc = pkg.get("desc", "")
        homepage = pkg.get("homepage", "")
        current = pkg.get("current", "")
        latest = pkg.get("latest", "")
        is_outdated = bool(current and latest)

        content = Text()
        content.append(f"{name}\n", style="bold cyan underline")
        if version:
            content.append("\nVersion: ", style="bold")
            content.append(f"{version}\n", style="white")
        if is_outdated:
            content.append("\nInstalled: ", style="bold")
            content.append(f"{current}\n", style="yellow")
            content.append("Available: ", style="bold")
            content.append(f"{latest}\n", style="green")
        if desc:
            content.append("\nDescription:\n", style="bold")
            content.append(f"{desc}\n", style="white")
        if homepage:
            content.append("\nHomepage: ", style="bold")
            content.append(f"{homepage}\n", style="blue underline")

        try:
            result = subprocess.run(
                ["brew", "info", name], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[:20]
                brew_info_text = "\n".join(lines)
                get_brew_cache().set(name, brew_info_text)
                content.append("\nBrew Info:\n", style="bold")
                content.append("-" * 40 + "\n", style="dim")
                content.append(brew_info_text, style="dim")
        except Exception:
            content.append("\n(Could not load brew info)\n", style="dim italic")

        self._content.update(content)

    # Symlink display
    def show_symlink(self, link: dict) -> None:
        self._clear_buttons()
        name = link.get("name", "Unknown")
        target = link.get("target", "")
        broken = link.get("broken", False)
        full_path = link.get("full_path", "")

        content = Text()
        content.append(f"Symlink: {name}\n\n", style="bold cyan underline")

        if broken:
            content.append("Status: ", style="bold")
            content.append("BROKEN\n\n", style="bold red")
            content.append("The target no longer exists.\n", style="red")
            content.append("\nTarget was: ", style="bold")
            content.append(f"{target}\n", style="dim")
            self._current_symlink = full_path or f"/opt/homebrew/bin/{name}"
        else:
            content.append("Status: ", style="bold")
            content.append("OK\n\n", style="bold green")
            content.append("Points to:\n", style="bold")
            content.append(f"{target}\n", style="white")
            self._current_symlink = None

        self._content.update(content)
        self._shown_welcome = True

        if broken:
            import time

            self.mount(
                Button(
                    "Delete Broken Symlink",
                    id=f"delete-symlink-btn-{int(time.time() * 1000)}",
                    variant="error",
                )
            )

    def show_broken_summary(self, broken_links: list) -> None:
        self._clear_buttons()
        self._all_broken_symlinks = [
            link.get("full_path", "") for link in broken_links if link.get("full_path")
        ]

        content = Text()
        content.append(
            f"Broken Symlinks ({len(broken_links)})\n\n", style="bold red underline"
        )
        content.append(
            "These symlinks point to targets that no longer exist:\n\n", style="dim"
        )

        for link in broken_links[:20]:
            name = link.get("name", "?")
            target = link.get("target", "?")
            content.append(f"  {name}\n", style="red")
            content.append(f"    -> {target}\n", style="dim")

        if len(broken_links) > 20:
            content.append(
                f"\n  ... and {len(broken_links) - 20} more\n", style="dim italic"
            )

        self._content.update(content)
        self._shown_welcome = True

        if self._all_broken_symlinks:
            import time

            self.mount(
                Button(
                    f"Delete All {len(self._all_broken_symlinks)} Broken",
                    id=f"delete-all-broken-{int(time.time() * 1000)}",
                    variant="error",
                )
            )

    def show_password_prompt(self, message: str, action: str) -> None:
        self._awaiting_password = True
        self._password_action = action

        content = Text()
        content.append("Authorization Required\n\n", style="bold yellow")
        content.append(f"{message}\n\n", style="dim")
        content.append("Enter your password below:\n", style="bold")
        self._content.update(content)

        import time

        ts = int(time.time() * 1000)
        pwd_input = Input(
            placeholder="Password (hidden)", password=True, id=f"sudo-password-{ts}"
        )
        self.mount(pwd_input)
        pwd_input.focus()
        self.mount(Button("Cancel", id=f"cancel-sudo-{ts}", variant="default"))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not self._awaiting_password:
            return
        password = event.value
        self._awaiting_password = False
        if self._password_action == "delete_one" and self._current_symlink:
            self.post_message(self.SudoDelete(self._current_symlink, password))
        elif self._password_action == "delete_all" and self._all_broken_symlinks:
            self.post_message(self.SudoDeleteAll(self._all_broken_symlinks, password))
        self._clear_buttons()
        self._content.update(Text("Processing...", style="dim italic"))

    # Command display
    def show_running_command(self, title: str, command: str) -> None:
        self._clear_buttons()
        content = Text()
        content.append(f"{title}\n\n", style="bold cyan underline")
        content.append("Running: ", style="bold")
        content.append(f"{command}\n\n", style="dim")
        content.append("Output:\n", style="bold")
        content.append("-" * 40 + "\n", style="dim")
        self._content.update(content)
        self._shown_welcome = True

    def append_output(self, text: str) -> None:
        current = self._content.renderable
        if isinstance(current, Text):
            current.append(text)
            self._content.update(current)
        else:
            new_content = Text(str(current))
            new_content.append(text)
            self._content.update(new_content)
        self._content.refresh()
        self.refresh()
        self.scroll_end(animate=False)

    def show_command_complete(
        self, title: str, success: bool, output: str = ""
    ) -> None:
        self._clear_buttons()
        content = Text()
        content.append(f"{title}\n\n", style="bold cyan underline")
        if success:
            content.append("Completed successfully!\n\n", style="bold green")
        else:
            content.append("Failed\n\n", style="bold red")
        if output:
            content.append("Output:\n", style="bold")
            content.append("-" * 40 + "\n", style="dim")
            lines = output.strip().split("\n")[-50:]
            content.append("\n".join(lines), style="white")
        self._content.update(content)
        self._shown_welcome = True

    # Executable display
    def show_executable(self, name: str, path: str) -> None:
        self._clear_buttons()
        content = Text()
        content.append(f"{name}\n", style="bold cyan underline")
        content.append(f"Location: {path}/{name}\n\n", style="dim")
        content.append("Loading help...\n", style="dim italic")
        self._content.update(content)
        self.set_timer(0.05, lambda: self._load_executable_help(name, path))

    def _load_executable_help(self, name: str, path: str) -> None:
        content = Text()
        content.append(f"{name}\n", style="bold cyan underline")
        content.append(f"Location: {path}/{name}\n\n", style="dim")

        try:
            result = subprocess.run(
                ["man", "-P", "cat", name], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")[:50]
                content.append("Man Page:\n", style="bold")
                content.append("-" * 40 + "\n", style="dim")
                content.append("\n".join(lines), style="white")
            else:
                self._add_help_output(name, path, content)
        except Exception:
            self._add_help_output(name, path, content)

        self._content.update(content)
        self._shown_welcome = True

    def _add_help_output(self, name: str, path: str, content: Text) -> None:
        try:
            result = subprocess.run(
                [f"{path}/{name}", "--help"], capture_output=True, text=True, timeout=2
            )
            output = result.stdout or result.stderr
            if output.strip():
                lines = output.strip().split("\n")[:30]
                content.append("Help (--help):\n", style="bold")
                content.append("-" * 40 + "\n", style="dim")
                content.append("\n".join(lines), style="white")
            else:
                content.append("No man page or --help available", style="dim italic")
        except Exception:
            content.append("No man page or --help available", style="dim italic")

    # Generic item display
    def show_item(self, item, item_type: str) -> None:
        self._clear_buttons()
        content = Text()
        type_labels = {
            "export": "Environment Variable",
            "path": "PATH Modification",
            "source": "Sourced File",
            "eval": "Eval Command",
        }

        if hasattr(item, "name"):
            name, value, raw_line, line_num = (
                item.name,
                item.value,
                item.raw_line,
                item.line_number,
            )
        else:
            name = item.get("name", "unknown")
            value = item.get("value", "")
            raw_line = item.get("raw_line", "")
            line_num = item.get("line_number", "?")

        label = type_labels.get(item_type, item_type.title())
        content.append(f"{label}\n\n", style="bold cyan underline")

        if item_type == "export":
            content.append(f"{name}", style="bold green")
            content.append(" = ", style="dim")
            content.append(f"{value}\n", style="white")
        elif item_type == "source":
            content.append("File: ", style="bold")
            content.append(f"{value}\n", style="magenta")
        elif item_type == "eval":
            content.append("Command: ", style="bold")
            content.append(f"{value}\n", style="blue")
        else:
            content.append(f"{raw_line}\n", style="white")

        content.append(f"\nDefined at line {line_num}", style="dim")
        self._content.update(content)
        self._shown_welcome = True

    def show_entry(self, entry: EnvEntry | None) -> None:
        self._clear_buttons()
        if entry is None:
            if not self._shown_welcome:
                self._content.update(self._get_welcome_text())
            return

        content = Text()
        content.append(f"{entry.name}\n", style="bold underline")
        content.append("\n")

        status_info = {
            Status.HEALTHY: ("OK", "green", "Working correctly."),
            Status.WARNING: ("Warning", "yellow", "Has a potential issue."),
            Status.ERROR: ("Error", "red", "Has a problem to fix."),
        }
        status_text, status_color, status_desc = status_info.get(
            entry.status, ("?", "white", "")
        )
        content.append("Status: ", style="bold")
        content.append(f"{status_text}\n", style=status_color)
        content.append(f"{status_desc}\n\n", style="dim")

        details = entry.details

        if details.get("description"):
            content.append(f"{details['description']}\n\n", style="italic")

        if details.get("issue"):
            content.append("Issue: ", style="bold red")
            content.append(f"{details['issue']}\n", style="red")
            if details.get("fix_suggestion"):
                content.append("Fix: ", style="bold yellow")
                content.append(f"{details['fix_suggestion']}\n\n", style="yellow")

        if entry.source_file:
            content.append("Defined in: ", style="bold")
            source = entry.source_file.replace("/Users/jrisberg/", "~/")
            content.append(f"{source}", style="cyan")
            if entry.source_line:
                content.append(f" (line {entry.source_line})", style="dim")
            content.append("\n\n")

        if "search_order" in details:
            content.append("PATH Position: ", style="bold")
            content.append(
                f"#{details['search_order']} of {details.get('total_paths', '?')}\n",
                style="cyan",
            )

        if "load_order" in details:
            content.append("Load Order: ", style="bold")
            content.append(f"#{details['load_order']}\n\n", style="cyan")

        if "version" in details:
            content.append("Version: ", style="bold")
            content.append(f"{details['version']}\n", style="cyan")

        self._content.update(content)
        self._shown_welcome = True

    # Button handler
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""

        # Homebrew buttons
        if btn_id.startswith("upgrade-btn") and self._current_package:
            self.post_message(self.UpgradePackage(self._current_package))
        elif btn_id.startswith("brew-update"):
            self.post_message(self.BrewUpdate())
        elif btn_id.startswith("brew-upgrade-all"):
            self.post_message(self.BrewUpgradeAll())
        elif btn_id.startswith("brew-uninstall") and self._current_package:
            self.post_message(self.BrewUninstallPackage(self._current_package))

        # Symlink buttons
        elif btn_id.startswith("delete-symlink-btn") and self._current_symlink:
            self.post_message(self.DeleteSymlink(self._current_symlink))
        elif btn_id.startswith("delete-all-broken") and self._all_broken_symlinks:
            self.post_message(self.DeleteAllBroken(self._all_broken_symlinks))
        elif btn_id.startswith("cancel-sudo"):
            self._awaiting_password = False
            self._clear_buttons()
            self._content.update(Text("Cancelled", style="dim"))

        # PIP buttons
        elif btn_id.startswith("pip-uninstall") and self._current_pip_package:
            pkg = self._current_pip_package
            self.post_message(
                self.UninstallPipPackage(pkg["name"], pkg["env_path"], pkg["is_system"])
            )

        # NPM buttons
        elif btn_id.startswith("npm-uninstall") and self._current_npm_package:
            pkg = self._current_npm_package
            self.post_message(
                self.UninstallNpmPackage(
                    pkg["name"], pkg["is_global"], pkg.get("project_path", "")
                )
            )
        elif btn_id.startswith("npm-upgrade-all"):
            self.post_message(self.NpmUpgradeAll())
        elif btn_id.startswith("npm-upgrade-") and self._current_npm_package:
            self.post_message(self.NpmUpgradePackage(self._current_npm_package["name"]))

        # Shell editing buttons
        elif btn_id.startswith("edit-alias"):
            self._show_edit_alias_form()
        elif btn_id.startswith("delete-alias") and self._current_alias_item:
            item = self._current_alias_item
            line_num = (
                item.line_number
                if hasattr(item, "line_number")
                else item.get("line_number", 0)
            )
            name = item.name if hasattr(item, "name") else item.get("name", "")
            self.post_message(
                self.DeleteAlias(self._current_shell_file, name, line_num)
            )
        elif btn_id.startswith("save-alias"):
            self._save_alias_from_form()
        elif btn_id.startswith("add-alias"):
            self._show_add_alias_form()
        elif btn_id.startswith("edit-function"):
            self._show_edit_function_form()
        elif btn_id.startswith("delete-function") and self._current_function_item:
            item = self._current_function_item
            name = item.name if hasattr(item, "name") else item.get("name", "")
            start = (
                item.line_number
                if hasattr(item, "line_number")
                else item.get("line_number", 0)
            )
            end = (
                getattr(item, "end_line", start)
                if hasattr(item, "end_line")
                else item.get("end_line", start)
            )
            self.post_message(
                self.DeleteFunction(self._current_shell_file, name, start, end)
            )
        elif btn_id.startswith("save-function"):
            self._save_function_from_form()
        elif btn_id.startswith("add-function"):
            self._show_add_function_form()
        elif btn_id.startswith("cancel-edit"):
            self._editing_alias = False
            self._editing_function = False
            if self._current_alias_item:
                self.show_alias(self._current_alias_item, self._current_shell_file)
            elif self._current_function_item:
                self.show_function(
                    self._current_function_item, self._current_shell_file
                )
            elif self._current_shell_file:
                import os

                self.show_shell_file_selected(
                    self._current_shell_file, os.path.basename(self._current_shell_file)
                )

    def clear(self) -> None:
        self._clear_buttons()
        self._content.update(self._get_welcome_text())
        self._shown_welcome = False
