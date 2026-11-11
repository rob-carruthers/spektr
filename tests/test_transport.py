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


def test_clockstate_bar_val_check() -> None:
    message: list[OscArg] = ["invalid", 1.0, 1.0, 1.0, 1.0]
    with pytest.raises(TypeError) as excinfo:
        ClockState.from_message(message)
    assert "bar" in str(excinfo)


def test_clockstate_beats_val_check() -> None:
    message: list[OscArg] = [1.0, "invalid", 1.0, 1.0, 1.0]
    with pytest.raises(TypeError) as excinfo:
        ClockState.from_message(message)
    assert "beats" in str(excinfo)


def test_clockstate_beats_per_second_val_check() -> None:
    message: list[OscArg] = [1.0, 1.0, "invalid", 1.0, 1.0]
    with pytest.raises(TypeError) as excinfo:
        ClockState.from_message(message)
    assert "beats_per_second" in str(excinfo)


def test_clockstate_beats_per_bar_val_check() -> None:
    message: list[OscArg] = [1.0, 1.0, 1.0, "invalid", 1.0]
    with pytest.raises(TypeError) as excinfo:
        ClockState.from_message(message)
    assert "beats_per_bar" in str(excinfo)


def test_clockstate_bar_start_beats_val_check() -> None:
    message: list[OscArg] = [1.0, 1.0, 1.0, 1.0, "invalid"]
    with pytest.raises(TypeError) as excinfo:
        ClockState.from_message(message)
    assert "bar_start_beats" in str(excinfo)
