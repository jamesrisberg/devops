from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Status(Enum):
    """Status of an environment entry."""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class EnvEntry:
    """Base class for environment entries."""
    name: str
    path: str
    status: Status = Status.HEALTHY
    source_file: str | None = None
    source_line: int | None = None
    details: dict[str, Any] = field(default_factory=dict)
    
    @property
    def status_icon(self) -> str:
        """Return status icon."""
        icons = {
            Status.HEALTHY: "[green]✓[/]" ,
            Status.WARNING: "[yellow]⚠[/]",
            Status.ERROR: "[red]✗[/]",
        }
        return icons.get(self.status, "?")


class BaseCollector(ABC):
    """Base class for environment collectors."""
    
    name: str = "base"
    description: str = "Base collector"
    
    @abstractmethod
    def collect(self) -> list[EnvEntry]:
        """Collect environment entries."""
        pass
    
    def refresh(self) -> list[EnvEntry]:
        """Refresh and return entries."""
        return self.collect()
