from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer

from devops.screens.main import MainScreen
from devops.screens.ffmpeg import FFmpegScreen
from devops.screens.imagemagick import ImageMagickScreen


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
        with TabbedContent(id="app-tabs"):
            with TabPane("Environment", id="env-pane"):
                yield MainScreen()
            with TabPane("FFmpeg", id="ffmpeg-pane"):
                yield FFmpegScreen()
            with TabPane("ImageMagick", id="magick-pane"):
                yield ImageMagickScreen()
        yield Footer()

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
        self.notify("Use arrow keys to navigate, Enter to expand, Tab to switch tabs, q to quit")
