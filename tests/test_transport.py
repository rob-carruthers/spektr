import pytest

from spektr.transport import ClockState, OscArg, Transport


def test_transport_creation() -> None:
    Transport()


@pytest.mark.integration
def test_ping() -> None:
    transport = Transport()
    transport.ping()


def test_clockstate_creation() -> None:
    message: list[OscArg] = [1.0, 1.0, 1.0, 1.0, 1.0]
    ClockState.from_message(message)


@pytest.mark.parametrize(("index", "name"), tuple(enumerate(ClockState._fields)))
def test_clockstate_rejects_non_float(index: int, name: str) -> None:
    message: list[OscArg] = [1.0 for _ in ClockState._fields]
    message[index] = 1
    with pytest.raises(TypeError, match=f"`{name}`"):
        ClockState.from_message(message)


def test_next_bar_valid() -> None:
    # bar, beats, beats_per_second, beats_per_bar, bar_start_beats
    message: list[OscArg] = [0.0, 0.5, 1.0, 4.0, 0.0]
    assert ClockState.from_message(message).next_bar_beats() == 4.0


def test_next_bar_valid_higher_tempo() -> None:
    # bar, beats, beats_per_second, beats_per_bar, bar_start_beats
    message: list[OscArg] = [0.0, 3.85, 2.0, 4.0, 0.0]
    assert ClockState.from_message(message).next_bar_beats(0.1) == 8.0


def test_next_bar_valid_overflow() -> None:
    # bar, beats, beats_per_second, beats_per_bar, bar_start_beats
    message: list[OscArg] = [0.0, 3.95, 1.0, 4.0, 0.0]
    assert ClockState.from_message(message).next_bar_beats(0.1) == 8.0


def test_next_bar_from_reanchored_grid() -> None:
    # We changed to 3 beats per bar precisely at beat 10.0
    message: list[OscArg] = [0.0, 11.0, 1.0, 3.0, 10.0]
    assert ClockState.from_message(message).next_bar_beats() == 13.0


def test_next_bar_from_reanchored_grid_overflow() -> None:
    # We changed to 3 beats per bar precisely at beat 10.0
    message: list[OscArg] = [0.0, 12.95, 1.0, 3.0, 10.0]
    assert ClockState.from_message(message).next_bar_beats(0.1) == 16.0
