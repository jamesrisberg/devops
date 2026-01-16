"""Animated ASCII loading widget."""

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

# Git-themed loading animation frames
GIT_FRAMES = [
    r"""
       .---.
      /     \
      \.@-@./
      /`\_/`\
     //  _  \\
    | \     )|_
   /`\_`>  <_/ \
   \__/'---'\__/
    """,
    r"""
       .---.
      /     \
      \.O-O./
      /`\_/`\
     //  _  \\
    | \     )|_
   /`\_`>  <_/ \
   \__/'---'\__/
    """,
    r"""
       .---.
      /     \
      \.o-o./
      /`\_/`\
     //  _  \\
    | \     )|_
   /`\_`>  <_/ \
   \__/'---'\__/
    """,
    r"""
       .---.
      /     \
      \.-.-./
      /`\_/`\
     //  _  \\
    | \     )|_
   /`\_`>  <_/ \
   \__/'---'\__/
    """,
]

# Spinner frames for a more subtle animation
SPINNER_FRAMES = [
    "[ =    ]",
    "[  =   ]",
    "[   =  ]",
    "[    = ]",
    "[     =]",
    "[    = ]",
    "[   =  ]",
    "[  =   ]",
    "[ =    ]",
    "[=     ]",
]

# Git branch animation
BRANCH_FRAMES = [
    r"""
   *
   |
   *
  /|\
  * * *
    """,
    r"""
   o
   |
   *
  /|\
  * * *
    """,
    r"""
   *
   |
   o
  /|\
  * * *
    """,
    r"""
   *
   |
   *
  /|\
  o * *
    """,
    r"""
   *
   |
   *
  /|\
  * o *
    """,
    r"""
   *
   |
   *
  /|\
  * * o
    """,
]

# Scanning/search animation
SCAN_FRAMES = [
    r"""
   .--------.
   |[      ]|
   |        |
   |________|
   /_______/
    """,
    r"""
   .--------.
   |[=     ]|
   |        |
   |________|
   /_______/
    """,
    r"""
   .--------.
   |[==    ]|
   |        |
   |________|
   /_______/
    """,
    r"""
   .--------.
   |[===   ]|
   |        |
   |________|
   /_______/
    """,
    r"""
   .--------.
   |[====  ]|
   |        |
   |________|
   /_______/
    """,
    r"""
   .--------.
   |[===== ]|
   |        |
   |________|
   /_______/
    """,
    r"""
   .--------.
   |[======]|
   |        |
   |________|
   /_______/
    """,
    r"""
   .--------.
   |[===== ]|
   |        |
   |________|
   /_______/
    """,
    r"""
   .--------.
   |[====  ]|
   |        |
   |________|
   /_______/
    """,
    r"""
   .--------.
   |[===   ]|
   |        |
   |________|
   /_______/
    """,
    r"""
   .--------.
   |[==    ]|
   |        |
   |________|
   /_______/
    """,
    r"""
   .--------.
   |[=     ]|
   |        |
   |________|
   /_______/
    """,
]

# Radar/pulse animation
RADAR_FRAMES = [
    r"""
      .
     /|\
    --*--
     \|/
      '
    """,
    r"""
      .
     /|\
    /-*-\
     \|/
      '
    """,
    r"""
     .-.
    / | \
   (--*--)
    \ | /
     '-'
    """,
    r"""
    .---.
   /  |  \
  (---*---)
   \  |  /
    '---'
    """,
    r"""
   .-----.
  /   |   \
 (----*----)
  \   |   /
   '-----'
    """,
    r"""
    .---.
   /  |  \
  (---*---)
   \  |  /
    '---'
    """,
    r"""
     .-.
    / | \
   (--*--)
    \ | /
     '-'
    """,
    r"""
      .
     /|\
    /-*-\
     \|/
      '
    """,
]


class LoadingAnimation(Static):
    """An animated ASCII art loading widget."""

    DEFAULT_CSS = """
    LoadingAnimation {
        height: auto;
        width: 100%;
        text-align: center;
    }
    """

    frame_index = reactive(0)

    def __init__(
        self,
        frames: list[str] | None = None,
        message: str = "Loading...",
        style: str = "cyan",
        interval: float = 0.15,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._frames = frames or RADAR_FRAMES
        self._message = message
        self._style = style
        self._interval = interval
        self._timer = None

    def on_mount(self) -> None:
        self._update_display()
        self._timer = self.set_interval(self._interval, self._next_frame)

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop()

    def _next_frame(self) -> None:
        self.frame_index = (self.frame_index + 1) % len(self._frames)

    def watch_frame_index(self, _: int) -> None:
        self._update_display()

    def _update_display(self) -> None:
        content = Text()
        content.append(self._frames[self.frame_index], style=self._style)
        content.append(f"\n{self._message}", style="bold")
        self.update(content)

    def set_message(self, message: str) -> None:
        """Update the loading message."""
        self._message = message
        self._update_display()

    def stop(self) -> None:
        """Stop the animation."""
        if self._timer:
            self._timer.stop()
            self._timer = None
