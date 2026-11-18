from spektr.event import NoteOff, NoteOn
from spektr.transport import Transport


def main() -> None:
    transport = Transport()
    sched_at = transport.clock_state.next_bar_beats()
    note1 = NoteOn(scheduled_at=sched_at, synth_name="legato1", freq=432)
    noteoff1 = NoteOff(scheduled_at=sched_at + 0.5, note_id=note1.note_id)
    transport.send_events(note1, noteoff1)
