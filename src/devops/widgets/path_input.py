"""Path input with autocomplete suggestions."""
import os
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, OptionList, Static
from textual.widget import Widget
from textual.binding import Binding
from textual.message import Message


class PathInput(Widget):
    """Input field with filesystem path autocomplete."""

    DEFAULT_CSS = """
    PathInput {
        height: auto;
        width: 100%;
    }

    PathInput > Input {
        width: 100%;
    }

    PathInput > #suggestions {
        height: auto;
        max-height: 10;
        width: 100%;
        background: $surface;
        border: solid $primary;
        display: none;
    }

    PathInput > #suggestions.visible {
        display: block;
    }

    PathInput > #suggestions > .option-list--option {
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "hide_suggestions", "Hide", show=False),
        Binding("tab", "complete", "Complete", show=False),
    ]

    class PathSelected(Message):
        """Emitted when a path is selected."""
        def __init__(self, path: str) -> None:
            self.path = path
            super().__init__()

    def __init__(self, placeholder: str = "", id: str = None, **kwargs):
        super().__init__(id=id, **kwargs)
        self._placeholder = placeholder
        self._current_suggestions = []

    def compose(self) -> ComposeResult:
        yield Input(placeholder=self._placeholder, id="path-field")
        yield OptionList(id="suggestions")

    @property
    def value(self) -> str:
        """Get current input value."""
        try:
            return self.query_one("#path-field", Input).value
        except:
            return ""

    @value.setter
    def value(self, val: str) -> None:
        """Set input value."""
        try:
            self.query_one("#path-field", Input).value = val
        except:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update suggestions as user types."""
        if event.input.id != "path-field":
            return
        
        path = event.value
        self._update_suggestions(path)

    def _update_suggestions(self, path: str) -> None:
        """Get filesystem suggestions for the path."""
        suggestions = self.query_one("#suggestions", OptionList)
        suggestions.clear_options()
        self._current_suggestions = []

        if not path:
            suggestions.remove_class("visible")
            return

        try:
            # Expand ~ to home directory
            expanded = os.path.expanduser(path)
            
            # Determine directory and prefix
            if os.path.isdir(expanded):
                base_dir = expanded
                prefix = ""
            else:
                base_dir = os.path.dirname(expanded) or "."
                prefix = os.path.basename(expanded).lower()
            
            if not os.path.isdir(base_dir):
                suggestions.remove_class("visible")
                return
            
            # Get matching entries
            matches = []
            try:
                for entry in os.scandir(base_dir):
                    name = entry.name
                    if name.startswith('.') and not prefix.startswith('.'):
                        continue  # Skip hidden unless explicitly typing .
                    if prefix == "" or name.lower().startswith(prefix):
                        if entry.is_dir():
                            matches.append((name + "/", True))
                        else:
                            matches.append((name, False))
            except PermissionError:
                pass
            
            # Sort: directories first, then files
            matches.sort(key=lambda x: (not x[1], x[0].lower()))
            matches = matches[:10]  # Limit to 10
            
            if matches:
                for name, is_dir in matches:
                    full_path = os.path.join(base_dir, name)
                    display = name
                    if is_dir:
                        display = "📁 " + name
                    else:
                        display = "📄 " + name
                    suggestions.add_option(display)
                    self._current_suggestions.append(full_path)
                
                suggestions.add_class("visible")
            else:
                suggestions.remove_class("visible")
        except Exception:
            suggestions.remove_class("visible")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle suggestion selection."""
        if event.option_list.id != "suggestions":
            return
        
        idx = event.option_index
        if 0 <= idx < len(self._current_suggestions):
            selected_path = self._current_suggestions[idx]
            inp = self.query_one("#path-field", Input)
            inp.value = selected_path
            
            suggestions = self.query_one("#suggestions", OptionList)
            suggestions.remove_class("visible")
            
            # If directory, update suggestions
            if selected_path.endswith("/"):
                self._update_suggestions(selected_path)
            else:
                self.post_message(self.PathSelected(selected_path))

    def action_hide_suggestions(self) -> None:
        """Hide the suggestions dropdown."""
        suggestions = self.query_one("#suggestions", OptionList)
        suggestions.remove_class("visible")

    def action_complete(self) -> None:
        """Complete with first suggestion."""
        if self._current_suggestions:
            selected_path = self._current_suggestions[0]
            inp = self.query_one("#path-field", Input)
            inp.value = selected_path
            if selected_path.endswith("/"):
                self._update_suggestions(selected_path)
            else:
                self.action_hide_suggestions()

    def focus(self) -> None:
        """Focus the input."""
        try:
            self.query_one("#path-field", Input).focus()
        except:
            pass
