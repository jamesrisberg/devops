"""Main screen with tabbed interface for environment visualization."""

import subprocess

import pyperclip
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static, TabbedContent, TabPane, Tree
from textual.worker import Worker, get_current_worker

from devops.actions import shell_edit
from devops.cache.brew_cache import get_brew_cache
from devops.cache.brew_list_cache import CacheKey, get_brew_list_cache
from devops.collectors.asdf import AsdfCollector
from devops.collectors.base import EnvEntry
from devops.collectors.homebrew import HomebrewCollector
from devops.collectors.homebrew_async import (
    BrewCollectResult,
    build_entries_from_result,
    collect_all_sync,
)
from devops.collectors.node import NodeCollector
from devops.collectors.npm import NpmCollector
from devops.collectors.path import PathCollector
from devops.collectors.python_envs import PythonEnvCollector
from devops.collectors.ruby import RubyCollector
from devops.collectors.rust import RustCollector
from devops.collectors.shell_config import ConfigItem, ShellConfigCollector
from devops.collectors.symlinks import SymlinkCollector
from devops.widgets.detail_panel import DetailPanel
from devops.widgets.env_tree import EnvTree


class MainScreen(Widget):
    """Main screen with tabbed interface for environment visualization."""

    DEFAULT_CSS = """
    MainScreen {
        height: 1fr;
        width: 100%;
    }

    TabbedContent {
        height: 100%;
    }

    .split-view {
        height: 1fr;
        width: 100%;
    }

    EnvTree {
        width: 40%;
        min-width: 40;
        height: 100%;
        border: solid $primary;
    }

    DetailPanel {
        width: 60%;
        min-width: 30;
        height: 100%;
        border: solid $secondary;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._path_collector = PathCollector()
        self._shell_collector = ShellConfigCollector()
        self._homebrew_collector = HomebrewCollector()
        self._python_collector = PythonEnvCollector()
        self._symlink_collector = SymlinkCollector()
        self._npm_collector = NpmCollector()

        # Conditional collectors - only create if available
        self._node_collector = NodeCollector() if NodeCollector.is_available() else None
        self._ruby_collector = RubyCollector() if RubyCollector.is_available() else None
        self._rust_collector = RustCollector() if RustCollector.is_available() else None
        self._asdf_collector = AsdfCollector() if AsdfCollector.is_available() else None

        self._brew_loaded = False
        self._python_loaded = False
        self._npm_loaded = False
        self._node_loaded = False
        self._ruby_loaded = False
        self._rust_loaded = False
        self._asdf_loaded = False

        # Background sync state
        self._brew_syncing = False

        # Confirmation skip flag
        self._skip_confirmations = False

    def compose(self) -> ComposeResult:
        with TabbedContent(id="main-tabs"):
            # Core tabs always present
            with TabPane("Shell", id="shell-tab"):
                with Horizontal(classes="split-view"):
                    yield EnvTree(
                        "Shell Config Load Order (c=collapse)", id="shell-tree"
                    )
                    yield DetailPanel(id="shell-detail")

            with TabPane("PATH", id="path-tab"):
                with Horizontal(classes="split-view"):
                    yield EnvTree("PATH Search Order (c=collapse)", id="path-tree")
                    yield DetailPanel(id="path-detail")

            with TabPane("Symlinks", id="symlinks-tab"):
                with Horizontal(classes="split-view"):
                    yield EnvTree("Symlinks (c=collapse)", id="symlinks-tree")
                    yield DetailPanel(id="symlinks-detail")

            with TabPane("Homebrew", id="brew-tab"):
                with Horizontal(classes="split-view"):
                    yield EnvTree("Homebrew Packages (loading...)", id="brew-tree")
                    yield DetailPanel(id="brew-detail")

            with TabPane("Python", id="python-tab"):
                with Horizontal(classes="split-view"):
                    yield EnvTree("Python Environments (loading...)", id="python-tree")
                    yield DetailPanel(id="python-detail")

            # Conditional language tabs
            if self._node_collector:
                with TabPane("Node", id="node-tab"):
                    with Horizontal(classes="split-view"):
                        yield EnvTree("Node.js Versions (loading...)", id="node-tree")
                        yield DetailPanel(id="node-detail")

            if self._ruby_collector:
                with TabPane("Ruby", id="ruby-tab"):
                    with Horizontal(classes="split-view"):
                        yield EnvTree("Ruby Versions (loading...)", id="ruby-tree")
                        yield DetailPanel(id="ruby-detail")

            if self._rust_collector:
                with TabPane("Rust", id="rust-tab"):
                    with Horizontal(classes="split-view"):
                        yield EnvTree("Rust Toolchains (loading...)", id="rust-tree")
                        yield DetailPanel(id="rust-detail")

            if self._asdf_collector:
                with TabPane("asdf", id="asdf-tab"):
                    with Horizontal(classes="split-view"):
                        yield EnvTree("asdf Plugins (loading...)", id="asdf-tree")
                        yield DetailPanel(id="asdf-detail")

            with TabPane("NPM", id="npm-tab"):
                with Horizontal(classes="split-view"):
                    yield EnvTree("NPM Packages (loading...)", id="npm-tree")
                    yield DetailPanel(id="npm-detail")

    def on_mount(self) -> None:
        self._load_fast_data()

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """Lazy load data when tab is activated and show welcome."""
        pane_id = event.pane.id if event.pane else ""

        if pane_id == "shell-tab":
            try:
                panel = self.query_one("#shell-detail", DetailPanel)
                panel.show_shell_welcome()
            except Exception:
                pass
        elif pane_id == "path-tab":
            try:
                panel = self.query_one("#path-detail", DetailPanel)
                panel.show_path_welcome()
            except Exception:
                pass
        elif pane_id == "symlinks-tab":
            try:
                panel = self.query_one("#symlinks-detail", DetailPanel)
                broken = self._get_broken_count()
                panel.show_symlinks_welcome(broken)
            except Exception:
                pass
        elif pane_id == "brew-tab":
            if not self._brew_loaded:
                self.app.notify("Loading Homebrew packages...", timeout=2)
                self.set_timer(0.1, self._load_brew_data)
            try:
                panel = self.query_one("#brew-detail", DetailPanel)
                outdated = self._get_outdated_count()
                panel.show_homebrew_welcome(outdated, loading=not self._brew_loaded)
            except Exception:
                pass
        elif pane_id == "python-tab":
            if not self._python_loaded:
                self.app.notify("Loading Python environments...", timeout=2)
                self.set_timer(0.1, self._load_python_data)
            try:
                panel = self.query_one("#python-detail", DetailPanel)
                detected = self._get_detected_python_sources()
                panel.show_python_welcome(detected)
            except Exception:
                pass
        elif pane_id == "node-tab":
            if not self._node_loaded:
                self.app.notify("Loading Node.js versions...", timeout=2)
                self.set_timer(0.1, self._load_node_data)
            try:
                panel = self.query_one("#node-detail", DetailPanel)
                manager = (
                    self._node_collector._detect_manager()
                    if self._node_collector
                    else "unknown"
                )
                panel.show_node_welcome(manager)
            except Exception:
                pass
        elif pane_id == "ruby-tab":
            if not self._ruby_loaded:
                self.app.notify("Loading Ruby versions...", timeout=2)
                self.set_timer(0.1, self._load_ruby_data)
            try:
                panel = self.query_one("#ruby-detail", DetailPanel)
                manager = (
                    self._ruby_collector._detect_manager()
                    if self._ruby_collector
                    else "unknown"
                )
                panel.show_ruby_welcome(manager)
            except Exception:
                pass
        elif pane_id == "rust-tab":
            if not self._rust_loaded:
                self.app.notify("Loading Rust toolchains...", timeout=2)
                self.set_timer(0.1, self._load_rust_data)
            try:
                panel = self.query_one("#rust-detail", DetailPanel)
                panel.show_rust_welcome()
            except Exception:
                pass
        elif pane_id == "asdf-tab":
            if not self._asdf_loaded:
                self.app.notify("Loading asdf plugins...", timeout=2)
                self.set_timer(0.1, self._load_asdf_data)
            try:
                panel = self.query_one("#asdf-detail", DetailPanel)
                plugins = self._get_asdf_plugins()
                panel.show_asdf_welcome(plugins)
            except Exception:
                pass
        elif pane_id == "npm-tab":
            if not self._npm_loaded:
                self.app.notify("Loading NPM packages...", timeout=2)
                self.set_timer(0.1, self._load_npm_data)
            try:
                panel = self.query_one("#npm-detail", DetailPanel)
                panel.show_npm_welcome()
            except Exception:
                pass

    def _get_outdated_count(self) -> int:
        """Get count of outdated homebrew packages."""
        try:
            tree = self.query_one("#brew-tree", EnvTree)
            for entry in tree._entries:
                if entry.details.get("type") == "outdated":
                    return entry.details.get("count", 0)
        except Exception:
            pass
        return 0

    def _get_broken_count(self) -> int:
        """Get count of broken symlinks."""
        try:
            tree = self.query_one("#symlinks-tree", EnvTree)
            total = 0
            for entry in tree._entries:
                total += entry.details.get("broken", 0)
            return total
        except Exception:
            pass
        return 0

    def _get_detected_python_sources(self) -> list:
        """Get list of detected Python environment sources."""
        try:
            tree = self.query_one("#python-tree", EnvTree)
            detected = []
            for entry in tree._entries:
                env_type = entry.details.get("type", "")
                if env_type == "conda":
                    detected.append("Conda environments")
                elif env_type == "pyenv":
                    detected.append("pyenv versions")
                elif env_type == "virtualenv":
                    detected.append("virtualenv/venv")
                elif env_type == "system":
                    detected.append("System Python")
                elif env_type == "homebrew":
                    detected.append("Homebrew Python")
            return list(set(detected))
        except Exception:
            pass
        return []

    def _get_asdf_plugins(self) -> list:
        """Get list of asdf plugins."""
        try:
            tree = self.query_one("#asdf-tree", EnvTree)
            return [entry.details.get("plugin", "") for entry in tree._entries]
        except Exception:
            pass
        return []

    def _load_fast_data(self) -> None:
        """Load fast collectors synchronously."""
        try:
            tree = self.query_one("#path-tree", EnvTree)
            tree.set_entries(self._path_collector.collect())
        except Exception as e:
            self.app.notify(f"PATH error: {e}", severity="error")

        try:
            tree = self.query_one("#shell-tree", EnvTree)
            tree.set_entries(self._shell_collector.collect())
        except Exception as e:
            self.app.notify(f"Shell error: {e}", severity="error")

        try:
            tree = self.query_one("#symlinks-tree", EnvTree)
            tree.set_entries(self._symlink_collector.collect())
        except Exception as e:
            self.app.notify(f"Symlinks error: {e}", severity="error")

    def _load_brew_data(self) -> None:
        """Load Homebrew data - first from cache, then sync in background."""
        cache = get_brew_list_cache()

        # Try to load from cache for instant display
        cached_formulae = cache.get(CacheKey.FORMULAE)
        cached_casks = cache.get(CacheKey.CASKS)
        cached_outdated = cache.get(CacheKey.OUTDATED)

        if cached_formulae is not None:
            # Show cached data immediately
            result = BrewCollectResult(
                formulae=cached_formulae,
                casks=cached_casks or [],
                outdated=cached_outdated or [],
                from_cache=True,
            )
            entries = build_entries_from_result(result)
            self._update_brew_tree(entries, from_cache=True)

        # Start background sync
        if not self._brew_syncing:
            self._start_brew_sync()

    def _start_brew_sync(self) -> None:
        """Start background sync of brew data."""
        self._brew_syncing = True
        self.run_worker(
            self._sync_brew_data_worker,
            name="brew_sync",
            thread=True,
            exclusive=True,
        )

    def _sync_brew_data_worker(self) -> BrewCollectResult:
        """Worker thread: Fetch fresh brew data."""
        return collect_all_sync(use_cache=False)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker completion."""
        if event.worker.name == "brew_sync":
            if event.state.name == "SUCCESS" and event.worker.result:
                result = event.worker.result
                entries = build_entries_from_result(result)
                self._update_brew_tree(entries, from_cache=False)
            elif event.state.name == "ERROR":
                self.app.notify("Failed to sync Homebrew data", severity="error")
            self._brew_syncing = False

    def _update_brew_tree(self, entries: list, from_cache: bool) -> None:
        """Update the brew tree with entries."""
        try:
            tree = self.query_one("#brew-tree", EnvTree)
            tree.set_entries(entries)

            if from_cache:
                tree.root.label = "Homebrew Packages (cached, syncing...)"
            else:
                tree.root.label = "Homebrew Packages (c=collapse)"

            self._brew_loaded = True

            # Update welcome panel
            try:
                panel = self.query_one("#brew-detail", DetailPanel)
                outdated = self._get_outdated_count()
                panel.show_homebrew_welcome(
                    outdated, loading=False, syncing=self._brew_syncing
                )
            except Exception:
                pass

            # Start background loading of brew info for packages
            package_names = []
            for e in entries:
                if e.details.get("type") == "category":
                    package_names.extend(
                        [p["name"] for p in e.details.get("packages", [])]
                    )

            get_brew_cache().load_all_in_background(package_names)

        except Exception as e:
            self.app.notify(f"Homebrew error: {e}", severity="error")

    def _load_python_data(self) -> None:
        """Load Python data."""
        try:
            tree = self.query_one("#python-tree", EnvTree)
            tree.set_entries(self._python_collector.collect())
            tree.root.label = "Python Environments (c=collapse)"
            self._python_loaded = True
        except Exception as e:
            self.app.notify(f"Python error: {e}", severity="error")

    def _load_node_data(self) -> None:
        """Load Node.js data."""
        if not self._node_collector:
            return
        try:
            tree = self.query_one("#node-tree", EnvTree)
            tree.set_entries(self._node_collector.collect())
            tree.root.label = "Node.js Versions (c=collapse)"
            self._node_loaded = True
        except Exception as e:
            self.app.notify(f"Node error: {e}", severity="error")

    def _load_ruby_data(self) -> None:
        """Load Ruby data."""
        if not self._ruby_collector:
            return
        try:
            tree = self.query_one("#ruby-tree", EnvTree)
            tree.set_entries(self._ruby_collector.collect())
            tree.root.label = "Ruby Versions (c=collapse)"
            self._ruby_loaded = True
        except Exception as e:
            self.app.notify(f"Ruby error: {e}", severity="error")

    def _load_rust_data(self) -> None:
        """Load Rust data."""
        if not self._rust_collector:
            return
        try:
            tree = self.query_one("#rust-tree", EnvTree)
            tree.set_entries(self._rust_collector.collect())
            tree.root.label = "Rust Toolchains (c=collapse)"
            self._rust_loaded = True
        except Exception as e:
            self.app.notify(f"Rust error: {e}", severity="error")

    def _load_asdf_data(self) -> None:
        """Load asdf data."""
        if not self._asdf_collector:
            return
        try:
            tree = self.query_one("#asdf-tree", EnvTree)
            tree.set_entries(self._asdf_collector.collect())
            tree.root.label = "asdf Plugins (c=collapse)"
            self._asdf_loaded = True
        except Exception as e:
            self.app.notify(f"asdf error: {e}", severity="error")

    def _load_npm_data(self) -> None:
        """Load NPM data."""
        try:
            tree = self.query_one("#npm-tree", EnvTree)
            tree.set_entries(self._npm_collector.collect())
            tree.root.label = "NPM Packages (c=collapse)"
            self._npm_loaded = True
        except Exception as e:
            self.app.notify(f"NPM error: {e}", severity="error")

    def refresh_data(self) -> None:
        """Refresh all data."""
        # Invalidate brew caches on manual refresh
        get_brew_list_cache().invalidate_all()

        self._brew_loaded = False
        self._python_loaded = False
        self._npm_loaded = False
        self._node_loaded = False
        self._ruby_loaded = False
        self._rust_loaded = False
        self._asdf_loaded = False
        self._load_fast_data()

        # Reload current tab if it's a slow one
        tabs = self.query_one("#main-tabs", TabbedContent)
        if tabs.active == "brew-tab":
            self._load_brew_data()
        elif tabs.active == "python-tab":
            self._load_python_data()
        elif tabs.active == "node-tab":
            self._load_node_data()
        elif tabs.active == "ruby-tab":
            self._load_ruby_data()
        elif tabs.active == "rust-tab":
            self._load_rust_data()
        elif tabs.active == "asdf-tab":
            self._load_asdf_data()
        elif tabs.active == "npm-tab":
            self._load_npm_data()

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        self._handle_node_selection(event.node)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        self._handle_node_selection(event.node)

    def _handle_node_selection(self, node) -> None:
        tree = node.tree
        tree_id = tree.id

        panel_map = {
            "path-tree": "path-detail",
            "shell-tree": "shell-detail",
            "brew-tree": "brew-detail",
            "python-tree": "python-detail",
            "symlinks-tree": "symlinks-detail",
            "node-tree": "node-detail",
            "ruby-tree": "ruby-detail",
            "rust-tree": "rust-detail",
            "asdf-tree": "asdf-detail",
            "npm-tree": "npm-detail",
        }

        panel_id = panel_map.get(tree_id)
        if not panel_id:
            return

        try:
            detail_panel = self.query_one(f"#{panel_id}", DetailPanel)
        except Exception:
            return

        node_data = node.data

        if node_data is None:
            return

        if isinstance(node_data, dict):
            if "executable" in node_data:
                detail_panel.show_executable(node_data["executable"], node_data["path"])
                return

            if "package" in node_data:
                detail_panel.show_package(node_data["package"])
                return

            if "outdated_packages" in node_data:
                detail_panel.show_outdated_summary(node_data["outdated_packages"])
                return

            if "symlink" in node_data:
                detail_panel.show_symlink(node_data["symlink"])
                return

            if "broken_links" in node_data:
                detail_panel.show_broken_summary(node_data["broken_links"])
                return

            # Pip package
            if "pip_package" in node_data:
                detail_panel.show_pip_package(
                    node_data["pip_package"],
                    node_data.get("env_type", ""),
                    node_data.get("env_path", ""),
                    node_data.get("is_system", False),
                )
                return

            # NPM package
            if "npm_package" in node_data:
                detail_panel.show_npm_package(
                    node_data["npm_package"],
                    node_data.get("pkg_type", "global"),
                    node_data.get("project_path", ""),
                )
                return

            # Node package
            if "node_package" in node_data:
                detail_panel.show_node_package(
                    node_data["node_package"],
                    node_data.get("manager", ""),
                    node_data.get("node_path", ""),
                )
                return

            # Ruby gem
            if "gem" in node_data:
                detail_panel.show_gem_package(
                    node_data["gem"],
                    node_data.get("manager", ""),
                    node_data.get("ruby_path", ""),
                )
                return

            # Cargo crate
            if "crate" in node_data:
                detail_panel.show_cargo_package(
                    node_data["crate"],
                    node_data.get("toolchain", ""),
                )
                return

            # asdf version
            if "asdf_version" in node_data:
                detail_panel.show_asdf_version(
                    node_data["asdf_version"],
                    node_data.get("plugin", ""),
                    node_data.get("is_current", False),
                )
                return

            item = node_data.get("item")
            item_type = node_data.get("type", "")

            if item is not None:
                if item_type == "function":
                    shell_file = node_data.get("shell_file", "")
                    detail_panel.show_function(item, shell_file)
                    return

                if item_type == "alias":
                    shell_file = node_data.get("shell_file", "")
                    try:
                        alias_cmd = f"alias {item.name}='{item.value}'"
                        pyperclip.copy(alias_cmd)
                        self.app.notify(f"Copied: {item.name}", timeout=2)
                    except Exception:
                        pass
                    detail_panel.show_alias(item, shell_file)
                    return

                detail_panel.show_item(item, item_type)
                return

        if isinstance(node_data, EnvEntry):
            details = node_data.details

            # Check for shell config file
            if "items" in details and "load_order" in details:
                detail_panel.show_shell_file_selected(node_data.path, node_data.name)
                return

            # Check for outdated category
            if details.get("type") == "outdated" and "packages" in details:
                detail_panel.show_outdated_summary(details["packages"])
                return

            # Check for homebrew category
            if details.get("type") == "category":
                outdated = self._get_outdated_count()
                detail_panel.show_homebrew_welcome(
                    outdated, loading=not self._brew_loaded
                )
                return

            detail_panel.show_entry(node_data)
            return

        if node.parent and node.parent.data and isinstance(node.parent.data, EnvEntry):
            detail_panel.show_entry(node.parent.data)

    # Shell config editing handlers
    def on_detail_panel_save_alias(self, event: DetailPanel.SaveAlias) -> None:
        """Handle save alias request."""
        try:
            if event.old_name:
                # Edit existing alias
                shell_edit.update_alias(
                    event.file_path,
                    event.old_name,
                    event.name,
                    event.value,
                    event.line_number,
                )
                self.app.notify(f"Updated alias: {event.name}", severity="information")
            else:
                # Add new alias
                shell_edit.add_alias(event.file_path, event.name, event.value)
                self.app.notify(f"Added alias: {event.name}", severity="information")

            # Refresh shell tree
            self._refresh_shell_tree()
        except Exception as e:
            self.app.notify(f"Error saving alias: {e}", severity="error")

    def on_detail_panel_delete_alias(self, event: DetailPanel.DeleteAlias) -> None:
        """Handle delete alias request."""
        try:
            shell_edit.delete_item(event.file_path, event.line_number, "alias")
            self.app.notify(f"Deleted alias: {event.name}", severity="information")
            self._refresh_shell_tree()
        except Exception as e:
            self.app.notify(f"Error deleting alias: {e}", severity="error")

    def on_detail_panel_save_function(self, event: DetailPanel.SaveFunction) -> None:
        """Handle save function request."""
        try:
            if event.start_line > 0:
                # Edit existing function
                shell_edit.update_function(
                    event.file_path,
                    event.name,
                    event.body,
                    event.start_line,
                    event.end_line,
                )
                self.app.notify(
                    f"Updated function: {event.name}", severity="information"
                )
            else:
                # Add new function
                shell_edit.add_function(event.file_path, event.name, event.body)
                self.app.notify(f"Added function: {event.name}", severity="information")

            self._refresh_shell_tree()
        except Exception as e:
            self.app.notify(f"Error saving function: {e}", severity="error")

    def on_detail_panel_delete_function(
        self, event: DetailPanel.DeleteFunction
    ) -> None:
        """Handle delete function request."""
        try:
            shell_edit.delete_item(
                event.file_path, event.start_line, "function", event.end_line
            )
            self.app.notify(f"Deleted function: {event.name}", severity="information")
            self._refresh_shell_tree()
        except Exception as e:
            self.app.notify(f"Error deleting function: {e}", severity="error")

    def _refresh_shell_tree(self) -> None:
        """Refresh the shell config tree."""
        try:
            tree = self.query_one("#shell-tree", EnvTree)
            tree.set_entries(self._shell_collector.collect())
        except Exception:
            pass

    # PIP uninstall handler
    def on_detail_panel_uninstall_pip_package(
        self, event: DetailPanel.UninstallPipPackage
    ) -> None:
        """Handle pip package uninstall request."""
        pkg = event.package_name
        env_path = event.env_path
        is_system = event.is_system

        cmd = [env_path, "-m", "pip", "uninstall", "-y", pkg]
        if is_system:
            cmd.insert(-1, "--break-system-packages")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                self.app.notify(f"Uninstalled {pkg}", severity="information")
                self._python_loaded = False
                self._load_python_data()
            else:
                self.app.notify(f"Failed to uninstall {pkg}", severity="error")
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    # NPM uninstall handler
    def on_detail_panel_uninstall_npm_package(
        self, event: DetailPanel.UninstallNpmPackage
    ) -> None:
        """Handle npm package uninstall request."""
        pkg = event.package_name
        is_global = event.is_global

        cmd = ["npm", "uninstall"]
        if is_global:
            cmd.append("-g")
        cmd.append(pkg)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                self.app.notify(f"Uninstalled {pkg}", severity="information")
                self._npm_loaded = False
                self._load_npm_data()
            else:
                self.app.notify(f"Failed to uninstall {pkg}", severity="error")
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    # Homebrew handlers
    def on_detail_panel_upgrade_package(
        self, event: DetailPanel.UpgradePackage
    ) -> None:
        """Handle package upgrade request."""
        pkg = event.package_name
        self.app.notify(f"Upgrading {pkg}...", timeout=3)
        self.set_timer(0.1, lambda: self._run_upgrade(pkg))

    def _run_upgrade(self, package_name: str) -> None:
        """Run brew upgrade in background."""
        try:
            result = subprocess.run(
                ["brew", "upgrade", package_name],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                self.app.notify(f"Upgraded {package_name}!", severity="information")
                # Invalidate caches for this package
                get_brew_list_cache().invalidate_for_upgrade(package_name)
                self._brew_loaded = False
                self._load_brew_data()
            else:
                self.app.notify(f"Failed to upgrade {package_name}", severity="error")
        except subprocess.TimeoutExpired:
            self.app.notify(f"Upgrade timed out for {package_name}", severity="error")
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    def on_detail_panel_brew_update(self, event: DetailPanel.BrewUpdate) -> None:
        """Handle brew update request."""
        self.app.notify("Running brew update...", timeout=3)
        self.set_timer(0.1, self._run_brew_update)

    def _run_brew_update(self) -> None:
        """Run brew update with live output."""
        try:
            panel = self.query_one("#brew-detail", DetailPanel)
            panel.show_running_command("Updating Homebrew", "brew update")
        except Exception:
            pass

        self._brew_update_process = subprocess.Popen(
            ["brew", "update"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._brew_update_output = []
        self.set_timer(0.1, self._poll_brew_update)

    def _poll_brew_update(self) -> None:
        """Poll brew update process for output."""
        if (
            not hasattr(self, "_brew_update_process")
            or self._brew_update_process is None
        ):
            return

        import fcntl
        import os

        while True:
            if self._brew_update_process.stdout is None:
                break
            try:
                fd = self._brew_update_process.stdout.fileno()
                fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                line = self._brew_update_process.stdout.readline()
                if line:
                    self._brew_update_output.append(line)
                    try:
                        panel = self.query_one("#brew-detail", DetailPanel)
                        panel.append_output(line)
                    except Exception:
                        pass
                else:
                    break
            except (BlockingIOError, IOError):
                break

        ret = self._brew_update_process.poll()
        if ret is None:
            self.set_timer(0.2, self._poll_brew_update)
        else:
            output = "".join(self._brew_update_output)
            try:
                panel = self.query_one("#brew-detail", DetailPanel)
                panel.show_command_complete("Update Homebrew", ret == 0, output)
            except Exception:
                pass

            if ret == 0:
                self.app.notify("Homebrew updated!", severity="information")
                # Invalidate outdated cache since brew update changes available versions
                get_brew_list_cache().invalidate_for_update()
            else:
                self.app.notify("Update had errors", severity="warning")

            self._brew_loaded = False
            self._load_brew_data()
            self._brew_update_process = None

    def on_detail_panel_brew_upgrade_all(
        self, event: DetailPanel.BrewUpgradeAll
    ) -> None:
        """Handle brew upgrade all request."""
        self.app.notify("Upgrading all packages...", timeout=5)
        self.set_timer(0.1, self._run_brew_upgrade_all)

    def _run_brew_upgrade_all(self) -> None:
        """Run brew upgrade with live output."""
        try:
            panel = self.query_one("#brew-detail", DetailPanel)
            panel.show_running_command("Upgrading All Packages", "brew upgrade")
        except Exception:
            pass

        self._brew_process = subprocess.Popen(
            ["brew", "upgrade"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._brew_output = []
        self.set_timer(0.1, self._poll_brew_upgrade)

    def _poll_brew_upgrade(self) -> None:
        """Poll brew upgrade process for output."""
        if not hasattr(self, "_brew_process") or self._brew_process is None:
            return

        import fcntl
        import os

        while True:
            if self._brew_process.stdout is None:
                break
            try:
                fd = self._brew_process.stdout.fileno()
                fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                line = self._brew_process.stdout.readline()
                if line:
                    self._brew_output.append(line)
                    try:
                        panel = self.query_one("#brew-detail", DetailPanel)
                        panel.append_output(line)
                    except Exception:
                        pass
                else:
                    break
            except (BlockingIOError, IOError):
                break

        ret = self._brew_process.poll()
        if ret is None:
            self.set_timer(0.2, self._poll_brew_upgrade)
        else:
            output = "".join(self._brew_output)
            try:
                panel = self.query_one("#brew-detail", DetailPanel)
                panel.show_command_complete("Upgrade All Packages", ret == 0, output)
            except Exception:
                pass

            if ret == 0:
                self.app.notify("All packages upgraded!", severity="information")
                # Invalidate all caches after upgrade all
                get_brew_list_cache().invalidate_all()
            else:
                self.app.notify("Upgrade had errors", severity="warning")

            self._brew_loaded = False
            self._load_brew_data()
            self._brew_process = None

    # Symlink handlers
    def on_detail_panel_delete_symlink(self, event: DetailPanel.DeleteSymlink) -> None:
        """Handle symlink delete request."""
        path = event.symlink_path
        self._pending_symlink_delete = path
        self._try_delete_symlink(path)

    def _try_delete_symlink(self, symlink_path: str) -> None:
        """Try to delete symlink, prompt for sudo if needed."""
        import os

        try:
            if os.path.islink(symlink_path):
                os.unlink(symlink_path)
                self.app.notify(f"Deleted {symlink_path}", severity="information")
                self._refresh_symlinks()
            else:
                self.app.notify(f"Not a symlink: {symlink_path}", severity="error")
        except PermissionError:
            try:
                panel = self.query_one("#symlinks-detail", DetailPanel)
                panel.show_password_prompt(f"Delete: {symlink_path}", "delete_one")
            except Exception:
                self.app.notify("Permission denied", severity="error")
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    def _refresh_symlinks(self) -> None:
        """Refresh symlinks tree."""
        try:
            tree = self.query_one("#symlinks-tree", EnvTree)
            tree.set_entries(self._symlink_collector.collect())
        except Exception:
            pass

    def on_detail_panel_delete_all_broken(
        self, event: DetailPanel.DeleteAllBroken
    ) -> None:
        """Handle delete all broken symlinks request."""
        self._pending_bulk_delete = event.symlink_paths
        if not event.symlink_paths:
            self.app.notify("No broken symlinks to delete", timeout=2)
            return
        count = len(event.symlink_paths)
        try:
            panel = self.query_one("#symlinks-detail", DetailPanel)
            panel.show_password_prompt(f"Delete {count} broken symlinks", "delete_all")
        except Exception:
            self.app.notify("Could not show password prompt", severity="error")

    def on_detail_panel_sudo_delete(self, event: DetailPanel.SudoDelete) -> None:
        """Handle sudo delete with password."""
        self._run_sudo_delete(event.path, event.password)

    def _run_sudo_delete(self, symlink_path: str, password: str) -> None:
        """Delete symlink using sudo."""
        try:
            proc = subprocess.Popen(
                ["sudo", "-S", "rm", symlink_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(input=password + "\n", timeout=10)
            if proc.returncode == 0:
                self.app.notify(f"Deleted {symlink_path}", severity="information")
                self._refresh_symlinks()
            else:
                if "incorrect password" in stderr.lower() or "sorry" in stderr.lower():
                    self.app.notify("Incorrect password", severity="error")
                else:
                    self.app.notify(f"Failed: {stderr.strip()}", severity="error")
        except subprocess.TimeoutExpired:
            self.app.notify("Operation timed out", severity="error")
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    def on_detail_panel_sudo_delete_all(self, event: DetailPanel.SudoDeleteAll) -> None:
        """Handle sudo delete all with password."""
        self._run_bulk_sudo_delete(event.paths, event.password)

    def _run_bulk_sudo_delete(self, paths: list, password: str) -> None:
        """Delete multiple symlinks using sudo."""
        deleted = 0
        failed = 0
        for path in paths:
            try:
                proc = subprocess.Popen(
                    ["sudo", "-S", "rm", path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                stdout, stderr = proc.communicate(input=password + "\n", timeout=10)
                if proc.returncode == 0:
                    deleted += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        self.app.notify(f"Deleted {deleted}, failed {failed}", severity="information")
        self._refresh_symlinks()
