"""FFmpeg command builder screen."""
import subprocess
import shutil
import os
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static, Button, Input, Select, TextArea, Checkbox
from textual.widget import Widget

from devops.widgets.path_input import PathInput


class FFmpegScreen(Widget):
    """FFmpeg command builder interface."""

    DEFAULT_CSS = """
    FFmpegScreen {
        height: 1fr;
        width: 100%;
    }

    .ffmpeg-container {
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

    .option-input {
        width: 100%;
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
        self._ffmpeg_installed = shutil.which("ffmpeg") is not None
        self._current_command = ["ffmpeg"]
        self._process = None

    def compose(self) -> ComposeResult:
        with Horizontal(classes="ffmpeg-container"):
            with VerticalScroll(classes="left-panel"):
                yield Static("FFmpeg Command Builder", classes="section-header")
                
                if not self._ffmpeg_installed:
                    yield Static("\n⚠ FFmpeg not installed!", id="not-installed")
                    yield Button("Install FFmpeg", id="install-ffmpeg", variant="warning")
                
                # Input file
                yield Static("\n📁 Input File", classes="section-header")
                yield PathInput(placeholder="Start typing path...", id="input-file")
                yield Static("Type path or drag file here", classes="help-text")
                
                # What do you want to do? (Toggles)
                yield Static("\n🎬 What do you want to do?", classes="section-header")
                yield Static("Toggle options to show their settings:", classes="help-text")
                
                yield Checkbox("Convert format", id="toggle-convert", classes="toggle-row")
                with Vertical(id="convert-options", classes="options-group hidden"):
                    yield Static("Output format:")
                    yield Select(
                        [(("MP4 (H.264)", "mp4")), (("WebM (VP9)", "webm")),
                         (("MOV", "mov")), (("MKV", "mkv")), (("AVI", "avi"))],
                        id="output-format", value="mp4"
                    )
                
                yield Checkbox("Compress / reduce size", id="toggle-compress", classes="toggle-row")
                with Vertical(id="compress-options", classes="options-group hidden"):
                    yield Static("Quality:")
                    yield Select(
                        [(("High quality (CRF 18)", "18")), (("Good (CRF 23)", "23")),
                         (("Medium (CRF 28)", "28")), (("Low/small (CRF 32)", "32"))],
                        id="quality", value="23"
                    )
                    yield Static("Encoding speed:")
                    yield Select(
                        [(("Fast", "fast")), (("Medium", "medium")), (("Slow (better)", "slow"))],
                        id="speed", value="medium"
                    )
                
                yield Checkbox("Resize video", id="toggle-resize", classes="toggle-row")
                with Vertical(id="resize-options", classes="options-group hidden"):
                    yield Static("Resolution:")
                    yield Select(
                        [(("4K (3840p)", "3840:-1")), (("1080p", "1920:-1")),
                         (("720p", "1280:-1")), (("480p", "854:-1")),
                         (("Custom", "custom"))],
                        id="resolution", value="1920:-1"
                    )
                    yield Input(placeholder="Custom: width:height", id="custom-res")
                
                yield Checkbox("Trim / cut video", id="toggle-trim", classes="toggle-row")
                with Vertical(id="trim-options", classes="options-group hidden"):
                    yield Static("Start time:")
                    yield Input(placeholder="00:00:00 or seconds", id="start-time")
                    yield Static("Duration:")
                    yield Input(placeholder="00:00:30 or seconds", id="duration")
                
                yield Checkbox("Extract audio only", id="toggle-audio", classes="toggle-row")
                with Vertical(id="audio-options", classes="options-group hidden"):
                    yield Static("Audio format:")
                    yield Select(
                        [(("MP3", "mp3")), (("AAC", "aac")), (("WAV", "wav")),
                         (("FLAC", "flac")), (("OGG", "ogg"))],
                        id="audio-format", value="mp3"
                    )
                    yield Static("Audio quality:")
                    yield Select(
                        [(("High (320k)", "320k")), (("Good (192k)", "192k")),
                         (("Medium (128k)", "128k"))],
                        id="audio-quality", value="192k"
                    )
                
                yield Checkbox("Remove audio", id="toggle-noaudio", classes="toggle-row")
                
                # Output file
                yield Static("\n📤 Output File", classes="section-header")
                yield PathInput(placeholder="Leave empty for auto", id="output-file")
                yield Static("Auto-generates based on input + options", classes="help-text")

            with Vertical(classes="right-panel"):
                yield Static("Command Preview", classes="section-header")
                yield Static("ffmpeg", id="command-preview")
                
                with Horizontal(classes="action-buttons"):
                    yield Button("▶ Run", id="run-cmd", variant="success")
                    yield Button("📋 Copy", id="copy-cmd", variant="primary")
                    yield Button("Clear", id="clear-cmd", variant="default")
                
                yield Static("\nOutput", classes="section-header")
                yield TextArea(id="output-area", read_only=True)

    def on_mount(self) -> None:
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
            "toggle-compress": "compress-options",
            "toggle-resize": "resize-options",
            "toggle-trim": "trim-options",
            "toggle-audio": "audio-options",
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
        """Build FFmpeg command based on selections."""
        cmd = ["ffmpeg", "-y"]  # -y to overwrite
        
        try:
            inp = self.query_one("#input-file", PathInput).value.strip()
            
            # Trim - start time before input for fast seeking
            if self.query_one("#toggle-trim", Checkbox).value:
                start = self.query_one("#start-time", Input).value.strip()
                if start:
                    cmd.extend(["-ss", start])
            
            # Input
            if inp:
                cmd.extend(["-i", inp])
            
            # Duration after input
            if self.query_one("#toggle-trim", Checkbox).value:
                dur = self.query_one("#duration", Input).value.strip()
                if dur:
                    cmd.extend(["-t", dur])
            
            # Audio extraction mode
            if self.query_one("#toggle-audio", Checkbox).value:
                cmd.append("-vn")  # No video
                fmt = self.query_one("#audio-format", Select).value
                qual = self.query_one("#audio-quality", Select).value
                
                if fmt == "mp3":
                    cmd.extend(["-c:a", "libmp3lame", "-b:a", qual])
                elif fmt == "aac":
                    cmd.extend(["-c:a", "aac", "-b:a", qual])
                elif fmt == "wav":
                    cmd.extend(["-c:a", "pcm_s16le"])
                elif fmt == "flac":
                    cmd.extend(["-c:a", "flac"])
                elif fmt == "ogg":
                    cmd.extend(["-c:a", "libvorbis", "-b:a", qual])
                
                # Output
                out = self.query_one("#output-file", PathInput).value.strip()
                if not out and inp:
                    base = os.path.splitext(inp)[0]
                    out = f"{base}.{fmt}"
                if out:
                    cmd.append(out)
            else:
                # Video processing
                out_fmt = "mp4"
                if self.query_one("#toggle-convert", Checkbox).value:
                    out_fmt = self.query_one("#output-format", Select).value
                    if out_fmt == "mp4":
                        cmd.extend(["-c:v", "libx264", "-c:a", "aac"])
                    elif out_fmt == "webm":
                        cmd.extend(["-c:v", "libvpx-vp9", "-c:a", "libopus"])
                    elif out_fmt == "mov":
                        cmd.extend(["-c:v", "libx264", "-c:a", "aac"])
                
                # Compression
                if self.query_one("#toggle-compress", Checkbox).value:
                    crf = self.query_one("#quality", Select).value
                    speed = self.query_one("#speed", Select).value
                    cmd.extend(["-crf", crf, "-preset", speed])
                
                # Resize
                if self.query_one("#toggle-resize", Checkbox).value:
                    res = self.query_one("#resolution", Select).value
                    if res == "custom":
                        custom = self.query_one("#custom-res", Input).value.strip()
                        if custom:
                            cmd.extend(["-vf", f"scale={custom}"])
                    else:
                        cmd.extend(["-vf", f"scale={res}"])
                
                # Remove audio
                if self.query_one("#toggle-noaudio", Checkbox).value:
                    cmd.append("-an")
                
                # Output
                out = self.query_one("#output-file", PathInput).value.strip()
                if not out and inp:
                    base = os.path.splitext(inp)[0]
                    suffix = "_output"
                    if self.query_one("#toggle-compress", Checkbox).value:
                        suffix = "_compressed"
                    elif self.query_one("#toggle-resize", Checkbox).value:
                        suffix = "_resized"
                    elif self.query_one("#toggle-trim", Checkbox).value:
                        suffix = "_trimmed"
                    out = f"{base}{suffix}.{out_fmt}"
                if out:
                    cmd.append(out)
            
            self._current_command = cmd
            preview = self.query_one("#command-preview", Static)
            # Format nicely
            if len(cmd) > 6:
                formatted = cmd[0] + " " + cmd[1] + " \\\n  " + " \\\n  ".join(
                    [" ".join(cmd[i:i+2]) for i in range(2, len(cmd), 2)]
                )
                preview.update(formatted)
            else:
                preview.update(" ".join(cmd))
        except Exception as e:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "install-ffmpeg":
            self._install_ffmpeg()
        elif event.button.id == "run-cmd":
            self._run_command()
        elif event.button.id == "copy-cmd":
            self._copy_command()
        elif event.button.id == "clear-cmd":
            self._clear_form()

    def _install_ffmpeg(self) -> None:
        output = self.query_one("#output-area", TextArea)
        output.load_text("Installing FFmpeg via Homebrew...\n")
        self._process = subprocess.Popen(
            ["brew", "install", "ffmpeg"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        self._output_lines = []
        self.set_timer(0.1, self._poll_process)

    def _run_command(self) -> None:
        inp = self.query_one("#input-file", PathInput).value.strip()
        if not inp:
            self.app.notify("Please specify an input file", severity="warning")
            return
        
        output = self.query_one("#output-area", TextArea)
        output.load_text(f"Running...\n\n")
        
        self._process = subprocess.Popen(
            self._current_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
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
            if ret == 0:
                self.app.notify("FFmpeg completed!")
            self._process = None

    def _copy_command(self) -> None:
        try:
            import pyperclip
            pyperclip.copy(" ".join(self._current_command))
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
