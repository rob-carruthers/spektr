"""Synths with equivalents in SuperCollider."""

from dataclasses import dataclass
from typing import ClassVar

from spektr.event import NoteOn


@dataclass(kw_only=True, frozen=True)
class Legato1(NoteOn):
    synth_name: ClassVar[str] = "legato1"
    freq: float | None = None
    amp: float | None = None
