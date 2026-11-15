from spektr.event import Note
from spektr.transport import Transport


def main() -> None:
    transport = Transport()
    sched_at = transport.clock_state.next_bar_beats()
    note = Note(scheduled_at=sched_at, freq=432, offset_beats=0)
    transport.spawn(note)
    note = Note(scheduled_at=sched_at, freq=500, offset_beats=0.5)
    transport.spawn(note)
