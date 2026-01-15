"""ImageMagick command builder screen."""

import os
import shutil
import subprocess

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, Select, Static, TextArea

from devops.widgets.path_input import PathInput


class ImageMagickScreen(Widget):
    """ImageMagick command builder interface."""

    DEFAULT_CSS = """
    ImageMagickScreen {
        height: 1fr;
        width: 100%;
    }

    .magick-container {
        height: 1fr;
        width: 100%;
    }

    .left-panel {
        width: 45%;
        height: 100%;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
    }

    .right-panel {
        width: 55%;
        height: 100%;
        border: solid $secondary;
        padding: 1;
        overflow-y: auto;
    }

    .section-header {
        background: $primary-darken-2;
        padding: 0 1;
        margin: 1 0 0 0;
        text-style: bold;
    }

    .option-label {
        margin-top: 1;
    }

    .help-text {
        color: $text-muted;
        text-style: italic;
    }

    .toggle-row {
        height: 3;
        margin-top: 1;
        margin-bottom: 0;
    }
    .options-group {
        height: auto;
        layout: vertical;
        border-left: solid $primary;
        padding: 1;
        margin-left: 2;
        margin-bottom: 1;
    }
    .options-group Static {
        height: auto;
        margin-top: 1;
    }

    .options-group Select {
        height: auto;
        margin-bottom: 1;
    }

    .options-group Input {
        margin-bottom: 1;
    }

    .hidden {
        display: none;
    }
    #command-preview {
        height: auto;
        min-height: 3;
        background: $surface;
        padding: 1;
        margin: 1 0;
        border: solid $primary;
    }

    #output-area {
        height: 1fr;
        min-height: 10;
        background: $surface;
    }

    .action-buttons {
        height: auto;
        width: 100%;
        margin-top: 1;
    }

    .action-buttons Button {
        margin-right: 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._magick_installed: bool | None = None  # Lazy check
        self._current_command = ["magick"]
        self._process = None

    def _check_magick_installed(self) -> bool:
        """Lazy check for ImageMagick installation."""
        if self._magick_installed is None:
            self._magick_installed = (
                shutil.which("magick") is not None
                or shutil.which("convert") is not None
            )
        return self._magick_installed

    def compose(self) -> ComposeResult:
        with Horizontal(classes="magick-container"):
            with VerticalScroll(classes="left-panel"):
                yield Static("ImageMagick Command Builder", classes="section-header")

                yield Static(
                    "\n⚠ ImageMagick not installed!",
                    id="not-installed",
                    classes="hidden",
                )
                yield Button(
                    "Install ImageMagick",
                    id="install-magick",
                    variant="warning",
                    classes="hidden",
                )

                # Input file
                yield Static("\n📁 Input File", classes="section-header")
                yield PathInput(placeholder="Path to image...", id="input-file")
                yield Static("e.g., ~/Pictures/photo.png", classes="help-text")

                # What to do (toggles)
                yield Static("\n🖼 What do you want to do?", classes="section-header")
                yield Static("Toggle options to show settings:", classes="help-text")

                # Convert format
                yield Checkbox(
                    "Convert format", id="toggle-convert", classes="toggle-row"
                )
                with Vertical(id="convert-options", classes="options-group hidden"):
                    yield Static("Output format:")
                    yield Select(
                        [
                            (("JPEG - small, photos", "jpg")),
                            (("PNG - lossless", "png")),
                            (("WebP - modern, small", "webp")),
                            (("GIF", "gif")),
                            (("TIFF - high quality", "tiff")),
                            (("PDF", "pdf")),
                        ],
                        id="output-format",
                        value="jpg",
                    )
                    yield Static("Quality (1-100):")
                    yield Select(
                        [
                            (("High (95)", "95")),
                            (("Good (85)", "85")),
                            (("Medium (75)", "75")),
                            (("Low (60)", "60")),
                        ],
                        id="quality",
                        value="85",
                    )

                # Resize
                yield Checkbox("Resize", id="toggle-resize", classes="toggle-row")
                with Vertical(id="resize-options", classes="options-group hidden"):
                    yield Static("Resize to:")
                    yield Select(
                        [
                            (("50%", "50%")),
                            (("25%", "25%")),
                            (("1920px wide", "1920x")),
                            (("1280px wide", "1280x")),
                            (("800px wide", "800x")),
                            (("Thumbnail 150px", "150x150")),
                            (("Custom", "custom")),
                        ],
                        id="resize",
                        value="50%",
                    )
                    yield Input(
                        placeholder="WxH or W% (e.g., 800x600)", id="resize-custom"
                    )

                # Crop
                yield Checkbox("Crop", id="toggle-crop", classes="toggle-row")
                with Vertical(id="crop-options", classes="options-group hidden"):
                    yield Static("Crop to:")
                    yield Select(
                        [
                            (("Square (1:1)", "1:1")),
                            (("16:9 widescreen", "16:9")),
                            (("4:3 standard", "4:3")),
                            (("Custom", "custom")),
                        ],
                        id="crop",
                        value="1:1",
                    )
                    yield Input(
                        placeholder="WxH+X+Y (e.g., 800x600+100+50)", id="crop-custom"
                    )

                # Rotate
                yield Checkbox(
                    "Rotate / Flip", id="toggle-rotate", classes="toggle-row"
                )
                with Vertical(id="rotate-options", classes="options-group hidden"):
                    yield Static("Rotation:")
                    yield Select(
                        [
                            (("90° clockwise", "90")),
                            (("90° counter-clockwise", "-90")),
                            (("180°", "180")),
                            (("Flip vertical", "flip")),
                            (("Flip horizontal", "flop")),
                            (("Auto-orient", "auto")),
                        ],
                        id="rotate",
                        value="90",
                    )

                # Adjustments
                yield Checkbox(
                    "Adjust colors", id="toggle-adjust", classes="toggle-row"
                )
                with Vertical(id="adjust-options", classes="options-group hidden"):
                    yield Static("Brightness (-100 to 100):")
                    yield Input(placeholder="e.g., 10", id="brightness")
                    yield Static("Contrast (-100 to 100):")
                    yield Input(placeholder="e.g., 10", id="contrast")
                    yield Static("Saturation (%):")
                    yield Input(
                        placeholder="e.g., 120 for more, 80 for less", id="saturation"
                    )

                # Effects
                yield Checkbox(
                    "Apply effects", id="toggle-effects", classes="toggle-row"
                )
                with Vertical(id="effects-options", classes="options-group hidden"):
                    yield Static("Blur:")
                    yield Input(placeholder="0x2 (radius x sigma)", id="blur")
                    yield Static("Sharpen:")
                    yield Input(placeholder="0x1", id="sharpen")

                # Strip metadata
                yield Checkbox(
                    "Strip metadata (smaller file)",
                    id="toggle-strip",
                    classes="toggle-row",
                )

                # Output
                yield Static("\n📤 Output File", classes="section-header")
                yield PathInput(placeholder="Auto-generated if empty", id="output-file")

            with Vertical(classes="right-panel"):
                yield Static("Command Preview", classes="section-header")
                yield Static("magick", id="command-preview")

                with Horizontal(classes="action-buttons"):
                    yield Button("▶ Run", id="run-cmd", variant="success")
                    yield Button("📋 Copy", id="copy-cmd", variant="primary")
                    yield Button("Clear", id="clear-cmd", variant="default")

                yield Static("\nOutput", classes="section-header")
                yield TextArea(id="output-area", read_only=True)

    def on_mount(self) -> None:
        # Lazy check for imagemagick - show warning if not installed
        if not self._check_magick_installed():
            try:
                self.query_one("#not-installed").styles.display = "block"
                self.query_one("#install-magick").styles.display = "block"
            except Exception:
                pass
        self._update_visibility()
        self._update_command_preview()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        self._update_visibility()
        self._update_command_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._update_command_preview()

    def on_select_changed(self, event: Select.Changed) -> None:
        self._update_command_preview()

    def _update_visibility(self) -> None:
        """Show/hide option groups based on toggles."""
        toggle_map = {
            "toggle-convert": "convert-options",
            "toggle-resize": "resize-options",
            "toggle-crop": "crop-options",
            "toggle-rotate": "rotate-options",
            "toggle-adjust": "adjust-options",
            "toggle-effects": "effects-options",
        }

        for toggle_id, options_id in toggle_map.items():
            try:
                toggle = self.query_one(f"#{toggle_id}", Checkbox)
                options = self.query_one(f"#{options_id}")
                if toggle.value:
                    options.styles.display = "block"
                else:
                    options.styles.display = "none"
            except Exception:
                pass

    def _update_command_preview(self) -> None:
        """Build ImageMagick command."""
        cmd = ["magick"]

        try:
            inp = self.query_one("#input-file", PathInput).value.strip()
            inp = os.path.expanduser(inp) if inp else ""
            if inp:
                cmd.append(inp)

            # Resize
            if self.query_one("#toggle-resize", Checkbox).value:
                resize = self.query_one("#resize", Select).value
                if resize == "custom":
                    custom = self.query_one("#resize-custom", Input).value.strip()
                    if custom:
                        cmd.extend(["-resize", custom])
                else:
                    cmd.extend(["-resize", resize])

            # Crop
            if self.query_one("#toggle-crop", Checkbox).value:
                crop = self.query_one("#crop", Select).value
                if crop == "custom":
                    custom = self.query_one("#crop-custom", Input).value.strip()
                    if custom:
                        cmd.extend(["-crop", custom, "+repage"])
                elif crop in ("1:1", "16:9", "4:3"):
                    cmd.extend(["-gravity", "center", "-crop", crop, "+repage"])

            # Rotate
            if self.query_one("#toggle-rotate", Checkbox).value:
                rotate = self.query_one("#rotate", Select).value
                if rotate == "auto":
                    cmd.append("-auto-orient")
                elif rotate == "flip":
                    cmd.append("-flip")
                elif rotate == "flop":
                    cmd.append("-flop")
                else:
                    cmd.extend(["-rotate", rotate])

            # Adjustments
            if self.query_one("#toggle-adjust", Checkbox).value:
                bright = self.query_one("#brightness", Input).value.strip() or "0"
                contrast = self.query_one("#contrast", Input).value.strip() or "0"
                if bright != "0" or contrast != "0":
                    cmd.extend(["-brightness-contrast", f"{bright}x{contrast}"])

                sat = self.query_one("#saturation", Input).value.strip()
                if sat:
                    cmd.extend(["-modulate", f"100,{sat},100"])

            # Effects
            if self.query_one("#toggle-effects", Checkbox).value:
                blur = self.query_one("#blur", Input).value.strip()
                if blur:
                    cmd.extend(["-blur", blur])
                sharpen = self.query_one("#sharpen", Input).value.strip()
                if sharpen:
                    cmd.extend(["-sharpen", sharpen])

            # Quality (if converting)
            if self.query_one("#toggle-convert", Checkbox).value:
                quality = self.query_one("#quality", Select).value
                cmd.extend(["-quality", quality])

            # Strip
            if self.query_one("#toggle-strip", Checkbox).value:
                cmd.append("-strip")

            # Output
            out = self.query_one("#output-file", PathInput).value.strip()
            out = os.path.expanduser(out) if out else ""
            if not out and inp:
                base, ext = os.path.splitext(inp)
                if self.query_one("#toggle-convert", Checkbox).value:
                    ext = "." + self.query_one("#output-format", Select).value
                suffix = "_edited"
                out = f"{base}{suffix}{ext}"
            if out:
                cmd.append(out)

            self._current_command = cmd
            preview = self.query_one("#command-preview", Static)
            if len(cmd) > 5:
                preview.update(" \\\n  ".join(cmd))
            else:
                preview.update(" ".join(cmd))
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "install-magick":
            self._install_magick()
        elif event.button.id == "run-cmd":
            self._run_command()
        elif event.button.id == "copy-cmd":
            self._copy_command()
        elif event.button.id == "clear-cmd":
            self._clear_form()

    def _install_magick(self) -> None:
        output = self.query_one("#output-area", TextArea)
        output.load_text("Installing ImageMagick...\n")
        self._process = subprocess.Popen(
            ["brew", "install", "imagemagick"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._output_lines = []
        self.set_timer(0.1, self._poll_process)

    def _run_command(self) -> None:
        inp = self.query_one("#input-file", PathInput).value.strip()
        inp = os.path.expanduser(inp) if inp else ""
        if not inp:
            self.app.notify("Please specify an input file", severity="warning")
            return

        # Check if input file exists
        if not os.path.isfile(inp):
            self.app.notify("Input file not found", severity="error")
            output = self.query_one("#output-area", TextArea)
            # Show diagnostic info about the path
            special_chars = [
                f"  pos {i}: U+{ord(c):04X}" for i, c in enumerate(inp) if ord(c) > 127
            ]
            special_info = "\n".join(special_chars) if special_chars else "  (none)"
            output.load_text(
                f"Error: File not found\n\n"
                f"Path: {inp}\n"
                f"Length: {len(inp)} chars\n\n"
                f"Special characters:\n{special_info}\n\n"
                f"This can happen if the filename contains special Unicode characters\n"
                f"(like macOS screen recordings which use narrow no-break spaces U+202F).\n\n"
                f"Try using the autocomplete to select the file."
            )
            return

        output = self.query_one("#output-area", TextArea)
        output.load_text("Running...\n\n")

        self._process = subprocess.Popen(
            self._current_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self._output_lines = []
        self.set_timer(0.1, self._poll_process)

    def _poll_process(self) -> None:
        if self._process is None:
            return

        import fcntl

        try:
            fd = self._process.stdout.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            line = self._process.stdout.readline()
            if line:
                self._output_lines.append(line)
                output = self.query_one("#output-area", TextArea)
                output.load_text("".join(self._output_lines[-50:]))
                output.scroll_end(animate=False)
        except (BlockingIOError, IOError):
            pass

        ret = self._process.poll()
        if ret is None:
            self.set_timer(0.2, self._poll_process)
        else:
            status = "\n✓ Done!" if ret == 0 else f"\n✗ Failed (code {ret})"
            self._output_lines.append(status)
            output = self.query_one("#output-area", TextArea)
            output.load_text("".join(self._output_lines[-50:]))
            output.scroll_end(animate=False)
            if ret == 0:
                self.app.notify("ImageMagick completed!")
            self._process = None

    def _copy_command(self) -> None:
        try:
            import pyperclip

            self.app.notify("Copied!")
        except:
            self.app.notify("Copy failed", severity="error")

    def _clear_form(self) -> None:
        for inp in self.query(Input):
            inp.value = ""
        for cb in self.query(Checkbox):
            cb.value = False
        self._update_visibility()
        self._update_command_preview()
        self.query_one("#output-area", TextArea).load_text("")
