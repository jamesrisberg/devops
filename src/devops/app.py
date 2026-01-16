from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Middle
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static

from devops.screens.ffmpeg import FFmpegScreen
from devops.screens.imagemagick import ImageMagickScreen
from devops.screens.main import MainScreen

LOGO_ART = r"""
       ██████╗ ███████╗██╗   ██╗ ██████╗ ██████╗ ███████╗
       ██╔══██╗██╔════╝██║   ██║██╔═══██╗██╔══██╗██╔════╝
       ██║  ██║█████╗  ██║   ██║██║   ██║██████╔╝███████╗
       ██║  ██║██╔══╝  ╚██╗ ██╔╝██║   ██║██╔═══╝ ╚════██║
       ██████╔╝███████╗ ╚████╔╝ ╚██████╔╝██║     ███████║
       ╚═════╝ ╚══════╝  ╚═══╝   ╚═════╝ ╚═╝     ╚══════╝
"""

# Console-style loading messages
LOADING_STEPS = [
    ("shell", "Loading shell configuration..."),
    ("path", "Scanning PATH directories..."),
    ("symlinks", "Analyzing symlinks..."),
    ("homebrew", "Connecting to Homebrew..."),
    ("python", "Detecting Python environments..."),
    ("ready", "Ready!"),
]


class ConsoleLoadingArt(Static):
    """Console-style animated loading splash screen."""

    step_index = reactive(0)
    char_index = reactive(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._lines: list[str] = []
        self._current_line = ""
        self._done = False

    def on_mount(self) -> None:
        self._update_display()
        self._timer = self.set_interval(0.008, self._next_char)

    def on_unmount(self) -> None:
        if hasattr(self, "_timer") and self._timer:
            self._timer.stop()

    def _next_char(self) -> None:
        if self._done:
            return

        if self.step_index >= len(LOADING_STEPS):
            self._done = True
            return

        _, message = LOADING_STEPS[self.step_index]

        if self.char_index < len(message):
            self.char_index += 1
            self._current_line = message[: self.char_index]
            self._update_display()
        else:
            # Line complete, move to next
            self._lines.append(message)
            self._current_line = ""
            self.step_index += 1
            self.char_index = 0
            self._update_display()

    def _update_display(self) -> None:
        content = Text()

        # Logo
        content.append(LOGO_ART, style="bold cyan")
        content.append("\n")
        content.append(
            "       Development Environment Topology Visualizer\n\n",
            style="dim italic",
        )

        # Console output
        for line in self._lines:
            if "Ready" in line:
                content.append(f"  > {line}\n", style="bold green")
            else:
                content.append(f"  > {line}\n", style="green")

        # Current typing line with cursor
        if self._current_line:
            content.append(f"  > {self._current_line}", style="green")
            content.append("█", style="bold green")  # Cursor
        elif not self._done and self.step_index < len(LOADING_STEPS):
            content.append("  > ", style="green")
            content.append("█", style="bold green")  # Cursor

        self.update(content)

    def stop(self) -> None:
        if hasattr(self, "_timer") and self._timer:
            self._timer.stop()
            self._timer = None

    @property
    def is_done(self) -> bool:
        return self._done


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

    #main-container {
        height: 1fr;
        width: 100%;
    }

    #app-tabs {
        height: 100%;
        width: 100%;
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
        from textual.containers import Container
        from textual.widgets import TabbedContent, TabPane

        yield Header(show_clock=False)
        # Loading screen shown first
        with Middle(id="loading-screen"):
            yield ConsoleLoadingArt(id="loading-art")
        # Empty container for main content - populated after animation
        yield Container(id="main-container")
        yield Footer()

    def on_mount(self) -> None:
        """Start mounting content in background thread while animation plays."""
        self._content_ready = False
        # Run heavy initialization in background thread
        self.run_worker(self._init_screens_worker, thread=True, name="init_screens")
        # Poll for completion
        self.set_timer(0.1, self._check_ready)

    def _init_screens_worker(self) -> dict:
        """Worker thread: Pre-initialize the screen objects."""
        # Create screen instances in background thread
        # (the heavy __init__ work happens here, off the main thread)
        return {
            "main": MainScreen(),
            "ffmpeg": FFmpegScreen(),
            "magick": ImageMagickScreen(),
        }

    def on_worker_state_changed(self, event) -> None:
        """Handle worker completion."""
        if event.worker.name == "init_screens" and event.state.name == "SUCCESS":
            # Screens are ready, now mount them (must be on main thread)
            screens = event.worker.result
            self._mount_screens(screens)
            self._content_ready = True

    def _mount_screens(self, screens: dict) -> None:
        """Mount pre-initialized screens."""
        from textual.widgets import TabbedContent, TabPane

        container = self.query_one("#main-container")
        tabs = TabbedContent(id="app-tabs")
        container.mount(tabs)

        env_pane = TabPane("Environment", id="env-pane")
        tabs.add_pane(env_pane)
        env_pane.mount(screens["main"])

        ffmpeg_pane = TabPane("FFmpeg", id="ffmpeg-pane")
        tabs.add_pane(ffmpeg_pane)
        ffmpeg_pane.mount(screens["ffmpeg"])

        magick_pane = TabPane("ImageMagick", id="magick-pane")
        tabs.add_pane(magick_pane)
        magick_pane.mount(screens["magick"])

    def _check_ready(self) -> None:
        """Check if animation is done and content is ready."""
        try:
            loading_art = self.query_one("#loading-art", ConsoleLoadingArt)
            # Wait for both animation AND content
            if not loading_art.is_done or not self._content_ready:
                self.set_timer(0.1, self._check_ready)
                return
            # All done - swap screens
            loading_art.stop()
            self.query_one("#loading-screen").styles.display = "none"
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
