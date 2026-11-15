import re
from dataclasses import dataclass


@dataclass(kw_only=True)
class Event:
    scheduled_at: float | None = None

    @property
    def type(self) -> str:
        """Convert camel case class name to snake case."""
        event_type = type(self).__name__
        return re.sub(r"(?<!^)(?=[A-Z])", "_", event_type).lower()


@dataclass(kw_only=True)
class Note(Event):
    freq: float
    offset_beats: float
