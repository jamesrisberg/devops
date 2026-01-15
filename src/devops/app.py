from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle
from textual.widgets import Footer, Header, Static

from devops.screens.ffmpeg import FFmpegScreen
from devops.screens.imagemagick import ImageMagickScreen
from devops.screens.main import MainScreen

LOADING_ART = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║       ██████╗ ███████╗██╗   ██╗ ██████╗ ██████╗ ███████╗  ║
║       ██╔══██╗██╔════╝██║   ██║██╔═══██╗██╔══██╗██╔════╝  ║
║       ██║  ██║█████╗  ██║   ██║██║   ██║██████╔╝███████╗  ║
║       ██║  ██║██╔══╝  ╚██╗ ██╔╝██║   ██║██╔═══╝ ╚════██║  ║
║       ██████╔╝███████╗ ╚████╔╝ ╚██████╔╝██║     ███████║  ║
║       ╚═════╝ ╚══════╝  ╚═══╝   ╚═════╝ ╚═╝     ╚══════╝  ║
║                                                           ║
║          Development Environment Topology Visualizer      ║
║                                                           ║
║                    Loading...                             ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""


class DevopsApp(App):
    """Development Environment Topology Visualizer."""

    TITLE = "devops"
    SUB_TITLE = "Development Environment Topology"

    CSS = """
    Screen {
        background: $surface;
        layout: vertical;
    }

    Header {
        height: 3;
        padding: 0 1;
    }

    #app-tabs {
        height: 1fr;
    }

    #loading-screen {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    #loading-art {
        width: auto;
        height: auto;
        color: $primary;
    }

    MainScreen, FFmpegScreen, ImageMagickScreen {
        height: 1fr;
    }

    .healthy {
        color: $success;
    }

    .warning {
        color: $warning;
    }

    .error {
        color: $error;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        from textual.widgets import TabbedContent, TabPane

        yield Header(show_clock=False)
        # Loading screen shown first
        with Middle(id="loading-screen"):
            yield Static(LOADING_ART, id="loading-art")
        # Main content hidden initially
        with TabbedContent(id="app-tabs", classes="hidden"):
            with TabPane("Environment", id="env-pane"):
                yield MainScreen()
            with TabPane("FFmpeg", id="ffmpeg-pane"):
                yield FFmpegScreen()
            with TabPane("ImageMagick", id="magick-pane"):
                yield ImageMagickScreen()
        yield Footer()

    def on_mount(self) -> None:
        """Switch from loading screen to main content after a brief delay."""
        self.set_timer(0.1, self._show_main_content)

    def _show_main_content(self) -> None:
        """Hide loading screen and show main content."""
        try:
            self.query_one("#loading-screen").styles.display = "none"
            self.query_one("#app-tabs").remove_class("hidden")
            # The detail panel already initializes with the main welcome text,
            # so we don't need to explicitly show any tab-specific welcome here.
            # The user will see the main app welcome until they interact.
        except Exception:
            pass

    def action_refresh(self) -> None:
        """Refresh all data."""
        try:
            main_screen = self.query_one(MainScreen)
            main_screen.refresh_data()
            self.notify("Data refreshed")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_help(self) -> None:
        """Show help."""
        self.notify(
            "Use arrow keys to navigate, Enter to expand, Tab to switch tabs, q to quit"
        )
