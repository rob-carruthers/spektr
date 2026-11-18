"""Events including notes."""

import itertools
import re
from dataclasses import asdict, dataclass, field

from spektr.types import OscArg

ID_COUNTER = itertools.count(1)


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

    def flatten(self) -> list[OscArg]:
        """Convert class attributes to a flat list.

        This allows a set of Events to be sent to SuperCollider in a flat stream, parsed and
        separated. Subclasses of Event and their dispatchers/handlers in SuperCollider should be
        coordinated. Order of attributes from subclasses of Event is preserved in output of
        flatten(), so these can be ingested in order in a handler.
        """
        output: list[OscArg] = [self.scheduled_at, self.type]
        args = [v for k, v in asdict(self).items() if k not in ("scheduled_at", "type")]
        return [*output, len(args), *args]


@dataclass(kw_only=True)
class NoteOn(Event):
    """A note on event.

    Spawns a new Synth.
    """

    note_id: int = field(default_factory=lambda: next(ID_COUNTER))
    synth_name: str
    freq: float


@dataclass(kw_only=True)
class NoteOff(Event):
    """A note off event, requiring a note_id from an already-spawned note."""

    note_id: int
