from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Input, Button


class PasswordModal(ModalScreen[str | None]):
    """Modal for entering sudo password."""

    DEFAULT_CSS = """
    PasswordModal {
        align: center middle;
    }

    PasswordModal > Vertical {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    PasswordModal > Vertical > Static {
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
    }

    PasswordModal > Vertical > Input {
        width: 100%;
        margin-bottom: 1;
    }

    PasswordModal > Vertical > Horizontal {
        width: 100%;
        height: auto;
        align: center middle;
    }

    PasswordModal > Vertical > Horizontal > Button {
        margin: 0 1;
    }
    """

    def __init__(self, message: str = "Enter sudo password:"):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.message)
            yield Input(placeholder="Password", password=True, id="password-input")
            with Horizontal():
                yield Button("OK", id="ok-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#password-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            password = self.query_one("#password-input", Input).value
            self.dismiss(password)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)
