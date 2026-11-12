import time
from collections.abc import Iterator

import pytest

from spektr.transport import (
    METER_SETTLE_SECONDS,
    NEXT_BAR_LEAD_SECONDS,
    ClockState,
    ExistingPendingMeterChangeError,
    OscArg,
    StaleClockStateError,
    Transport,
)

EPSILON = 1e-3


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
    excluded = ("requested_at", "expiry")
    if name in excluded:
        return
    message: list[OscArg] = [1.0 for _ in ClockState._fields if _ not in excluded]
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
    assert ClockState.from_message(message).next_bar_beats() == 8.0


def test_next_bar_valid_overflow() -> None:
    # bar, beats, beats_per_second, beats_per_bar, bar_start_beats
    message: list[OscArg] = [0.0, 3.95, 1.0, 4.0, 0.0]
    assert ClockState.from_message(message).next_bar_beats() == 8.0


def test_next_bar_from_reanchored_grid() -> None:
    # We changed to 3 beats per bar precisely at beat 10.0
    message: list[OscArg] = [0.0, 11.0, 1.0, 3.0, 10.0]
    assert ClockState.from_message(message).next_bar_beats() == 13.0


def test_next_bar_from_reanchored_grid_overflow() -> None:
    # We changed to 3 beats per bar precisely at beat 10.0
    message: list[OscArg] = [0.0, 12.95, 1.0, 3.0, 10.0]
    assert ClockState.from_message(message).next_bar_beats() == 16.0


def test_clock_state_expiry() -> None:
    message: list[OscArg] = [0.0, 12.95, 1.0, 3.0, 10.0]
    state = ClockState.from_message(message, expiry=0.01)
    time.sleep(0.02)

    with pytest.raises(StaleClockStateError):
        _ = state.next_bar_beats()


@pytest.mark.integration
def test_clock_state_caching() -> None:
    transport = Transport()
    h1 = transport.clock_state
    h2 = transport.clock_state
    assert h1 is h2


@pytest.mark.integration
def test_clock_state_refresh() -> None:
    ttl = 0.01
    transport = Transport(ttl)
    h1 = transport.clock_state
    time.sleep(ttl * 2)
    h2 = transport.clock_state
    assert h1 is not h2
    assert h2.requested_at > h1.requested_at
    assert h2.beats > h1.beats


@pytest.fixture
def integration_transport() -> Transport:
    return Transport()


@pytest.mark.integration
def wait_for_beat(
    integration_transport: Transport,
    beat: float,
    timeout: float = 20.0,
) -> ClockState:
    """Poll SC until its clock reaches `beat`, returning that state."""
    deadline = time.monotonic() + timeout
    while True:
        state = integration_transport.get_clock_state()
        if state.beats >= beat:
            return state
        if time.monotonic() > deadline:
            pytest.fail(f"SC did not reach beat {beat} (stuck at {state.beats})")
        time.sleep(0.02)


@pytest.fixture
def meter_restored(integration_transport: Transport) -> Iterator[Transport]:
    """Yield a transport, then put SC back to 4/4 whatever the test did."""
    yield integration_transport
    deadline = time.monotonic() + 20.0
    while True:
        try:
            at = integration_transport.set_meter(4, 4)
            break
        except ExistingPendingMeterChangeError:
            if time.monotonic() > deadline:
                raise
            time.sleep(0.05)
    bps = integration_transport.get_clock_state().beats_per_second
    wait_for_beat(integration_transport, at + METER_SETTLE_SECONDS * bps)


@pytest.mark.integration
def test_beats_track_wall_clock(integration_transport: Transport) -> None:
    first = integration_transport.get_clock_state()
    time.sleep(1.0)
    second = integration_transport.get_clock_state()
    wall = second.requested_at - first.requested_at
    assert second.beats - first.beats == pytest.approx(wall * first.beats_per_second, abs=0.05)


@pytest.mark.integration
def test_bar_start_invariant(integration_transport: Transport) -> None:
    previous = integration_transport.get_clock_state()
    end = time.monotonic() + 5.0
    while time.monotonic() < end:
        state = integration_transport.get_clock_state()
        assert -EPSILON <= state.beats - state.bar_start_beats <= state.beats_per_bar + EPSILON
        assert state.beats >= previous.beats
        assert state.bar >= previous.bar
        previous = state
        time.sleep(0.02)


@pytest.mark.integration
def test_next_bar_beats_is_a_future_bar_line(integration_transport: Transport) -> None:
    state = integration_transport.get_clock_state()
    target = state.next_bar_beats()
    lead_beats = NEXT_BAR_LEAD_SECONDS * state.beats_per_second
    assert target - state.beats >= lead_beats
    assert target - state.beats <= 2 * state.beats_per_bar
    bars = (target - state.bar_start_beats) / state.beats_per_bar
    assert bars == pytest.approx(round(bars))


@pytest.mark.integration
def test_stale_state_refuses_next_bar_beats(integration_transport: Transport) -> None:
    state = integration_transport.get_clock_state()
    stale = state._replace(requested_at=state.requested_at - 10.0)
    with pytest.raises(StaleClockStateError):
        stale.next_bar_beats()


@pytest.mark.integration
@pytest.mark.parametrize(("upper", "lower"), [(0, 4), (4, 0), (-3, 4), (3, -4)])
def test_set_meter_rejects_non_positive(
    integration_transport: Transport,
    upper: int,
    lower: int,
) -> None:
    with pytest.raises(ValueError, match="should be > 0"):
        integration_transport.set_meter(upper, lower)


@pytest.mark.integration
def test_meter_change_in_the_past_is_refused(meter_restored: Transport) -> None:
    transport = meter_restored
    state = transport.get_clock_state()
    response = transport.request("/set/beats_per_bar", 3.0, state.beats - 1.0)
    assert response[0] == "late"
    time.sleep(0.3)  # a wrongly accepted change would have run straight away
    assert transport.get_clock_state().beats_per_bar == 4.0


@pytest.mark.integration
def test_second_meter_change_while_pending_is_refused(meter_restored: Transport) -> None:
    transport = meter_restored
    transport.set_meter(3, 4)
    with pytest.raises(ExistingPendingMeterChangeError):
        transport.set_meter(5, 4)


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.parametrize(("upper", "lower", "beats_per_bar"), [(3, 4, 3.0), (7, 8, 3.5)])
def test_meter_change_takes_effect(
    meter_restored: Transport,
    upper: int,
    lower: int,
    beats_per_bar: float,
) -> None:
    transport = meter_restored
    settle_beats = METER_SETTLE_SECONDS * transport.get_clock_state().beats_per_second

    at = transport.set_meter(upper, lower)

    after = wait_for_beat(transport, at + settle_beats)
    assert after.beats_per_bar == beats_per_bar
    assert after.bar_start_beats == pytest.approx(at, abs=EPSILON)

    next_bar = wait_for_beat(transport, at + beats_per_bar + settle_beats)
    assert next_bar.bar_start_beats == pytest.approx(at + beats_per_bar, abs=EPSILON)
