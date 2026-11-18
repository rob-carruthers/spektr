from spektr.synths import Legato1
from spektr.transport import Transport


def main() -> None:  # noqa: D103
    transport = Transport()
    sched_at = transport.clock_state.next_bar_beats()
    note1 = Legato1(at=sched_at, freq=432, amp=0.5)

    events = [note1]

    n = 20
    for i in range(20):
        change = note1.change(sched_at + i / n, freq=432 + (i * n), amp=0.2)
        events.append(change)

    events.append(note1.off(at=sched_at + 1.0))
    transport.send_events(*events)
