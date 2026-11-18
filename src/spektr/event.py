"""Events including notes."""

import itertools
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from typing import ClassVar, override

from spektr.types import OscArg

ID_COUNTER = itertools.count(1)


@dataclass(kw_only=True, frozen=True)
class Event:
    """A base Event to be sent to SuperCollider.

    Attributes
    ----------
    at : float
        When the event should be scheduled after being sent to SuperCollider.

    """

    at: float
    wire_type: ClassVar[str | None] = None

    @property
    def type(self) -> str:
        """Get the type of this event as snake case."""
        if self.wire_type is not None:
            return self.wire_type
        return re.sub(r"(?<!^)(?=[A-Z])", "_", type(self).__name__).lower()

    def wire_args(self) -> list[OscArg]:
        """Gather arguments for the relevant operation in SuperCollider."""
        args: list[OscArg] = []
        for f in fields(self):
            if f.name == "at":
                continue
            value = getattr(self, f.name)
            if isinstance(value, Mapping):
                for k, v in value.items():
                    args += [k, float(v)]
            else:
                args.append(value)
        return args

    def flatten(self) -> list[OscArg]:
        """Create flattened list of arguments to send in event stream to SuperCollider."""
        args = self.wire_args()
        return [self.at, self.type, len(args), *args]


@dataclass(kw_only=True, frozen=True)
class NoteEvent(Event):
    """A note event holding a local ID for lookup later in SuperCollider."""

    note_id: int


@dataclass(kw_only=True, frozen=True)
class NoteOn(NoteEvent):
    """A generic NoteOn, which must be subclassed to create synths with specific params."""

    wire_type: ClassVar[str | None] = "note_on"
    synth_name: ClassVar[str]
    note_id: int = field(default_factory=lambda: next(ID_COUNTER))

    def _control_names(self) -> set[str]:
        return {f.name for f in fields(self)} - {"at", "note_id"}

    def __post_init__(self) -> None:  # noqa: D105
        if not hasattr(type(self), "synth_name"):
            msg = f"{type(self).__name__} has no synth_name; subclass NoteOn"
            raise TypeError(msg)

    def controls(self) -> dict[str, float]:
        """Return key/value pairs for synth controls and values."""
        values = {n: getattr(self, n) for n in self._control_names()}
        return {k: v for k, v in values.items() if v is not None}

    @override
    def wire_args(self) -> list[OscArg]:
        pairs = [x for k, v in self.controls().items() for x in (k, float(v))]
        return [self.note_id, self.synth_name, *pairs]

    def change(self, at: float, **params: float) -> "NoteSet":
        """Schedule a change to an existing synth's params."""
        unknown_params = params.keys() - self._control_names()
        if unknown_params:
            msg = f"{type(self).__name__} has no control(s) {sorted(unknown_params)}"
            raise TypeError(msg)
        return NoteSet(at=at, note_id=self.note_id, params=params)

    def off(self, at: float) -> "NoteOff":
        """Schedule a note off of this synth."""
        return NoteOff(at=at, note_id=self.note_id)


@dataclass(kw_only=True, frozen=True)
class NoteSet(NoteEvent):
    """A note change event."""

    params: Mapping[str, float]


@dataclass(kw_only=True, frozen=True)
class NoteOff(NoteEvent):
    """A note off event."""
