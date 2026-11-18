"""Events including notes."""

import re
from dataclasses import dataclass


@dataclass(kw_only=True)
class Event:
    """A base Event to be sent to SuperCollider.

    Attributes
    ----------
    scheduled_at : float, default 0.0
        When the event should be scheduled when sent to SuperCollider. This defaults to 0.0 but
        should always be overriden by logic deciding when the event should be scheduled.

    """

    scheduled_at: float = 0.0

    @property
    def type(self) -> str:
        """Convert camel case class name to snake case."""
        event_type = type(self).__name__
        return re.sub(r"(?<!^)(?=[A-Z])", "_", event_type).lower()


@dataclass(kw_only=True)
class Note(Event):
    freq: float
    offset_beats: float
