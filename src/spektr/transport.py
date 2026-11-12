"""Transport, communication between Python and SuperCollider via OSC."""

import itertools
import math
import time
from threading import Lock
from typing import NamedTuple, Self

from pythonosc.udp_client import SimpleUDPClient

SCLANG_PORT = 57120

type OscArg = int | float | str | bytes | bool | list[OscArg] | None


def _as_float(name: str, value: OscArg) -> float:
    if not isinstance(value, float):
        msg = f"`{name}` should be float, got {type(value).__name__}: {value!r}"
        raise TypeError(msg)
    return value


METER_SETTLE_SECONDS = 0.1
NEXT_BAR_LEAD_SECONDS = 0.1


class Meter(NamedTuple):
    """A meter in time signature form, with a record of when SC changed to this meter."""

    upper: int
    lower: int
    changed_at_beats: float


class ExistingPendingMeterChangeError(ValueError):
    """Raised when SC received a meter change when another was already requested and pending."""


class LateMeterChangeError(Exception):
    """Raised when SC received a meter change after its target beat had passed."""


class StaleClockStateError(ValueError):
    """Raise if clock state is used too late after it was requested."""


class ClockState(NamedTuple):
    """Holder of last-reported clock state of SuperCollider.

    This should be considered ephemeral as the output of transport callers such as
    get_clock_state(). As such, instance methods should implement
    """

    bar: int
    beats: float
    beats_per_second: float
    beats_per_bar: float
    bar_start_beats: float
    requested_at: float
    expiry: float

    @classmethod
    def from_message(
        cls,
        params: list[OscArg],
        requested_at: float | None = None,
        expiry: float = 0.1,
    ) -> Self:
        """Construct a ClockState from an OSC message response."""
        bar, beats, beats_per_second, beats_per_bar, bar_start_beats = params
        bar = _as_float("bar", bar)
        beats = _as_float("beats", beats)
        beats_per_second = _as_float("beats_per_second", beats_per_second)
        beats_per_bar = _as_float("beats_per_bar", beats_per_bar)
        bar_start_beats = _as_float("bar_start_beats", bar_start_beats)
        if requested_at is None:
            requested_at = time.monotonic()

        return cls(
            int(bar),
            beats,
            beats_per_second,
            beats_per_bar,
            bar_start_beats,
            requested_at,
            expiry,
        )

    @property
    def bpm(self) -> float:  # noqa: D102
        return self.beats_per_second * 60.0

    def is_stale(self) -> bool:
        """Check if this ClockState has become stale."""
        return time.monotonic() > (self.requested_at + self.expiry)

    def next_bar_beats(self, min_seconds: float = NEXT_BAR_LEAD_SECONDS) -> float:
        """Return the absolute beat of the next bar line.

        If that bar line is closer than `min_seconds`, return the following one.
        Raises StaleClockStateError if this snapshot has expired.
        """
        if self.is_stale():
            age = time.monotonic() - self.requested_at
            msg = f"clock state is {age:.3f}s old (limit {self.expiry}s)"
            raise StaleClockStateError(msg)

        min_beats = min_seconds * self.beats_per_second
        boundary = self.bar_start_beats + self.beats_per_bar
        if boundary - self.beats < min_beats:
            boundary += self.beats_per_bar
        return boundary


class Transport:
    """Transport class holding an OSC SimpleUDPClient."""

    def __init__(self, clock_state_timeout: float = 0.05) -> None:
        """Initialize OSC client and test ping."""
        self.client = SimpleUDPClient("127.0.0.1", SCLANG_PORT)
        self._lock = Lock()
        self._ids = itertools.count(1)
        self._clock_state_timeout = clock_state_timeout
        self._cached_state: ClockState | None = None
        self._last_meter_change: Meter | None = None

    def request(self, address: str, *args: OscArg, timeout: float = 0.1) -> list[OscArg]:
        """Send a message to SC and gather the response."""
        with self._lock:
            request_id = next(self._ids)
            self.client.send_message(address, [request_id, *args])
            deadline = time.monotonic() + timeout
            error_msg = f"No reply to {address} within {timeout}s"
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(error_msg)

                try:
                    message = next(self.client.get_messages(remaining))
                except StopIteration:
                    raise TimeoutError(error_msg) from None

                if not message.params or message.params[0] != request_id:
                    continue  # stale or unrelated reply

                if message.address != address:
                    msg = (
                        f"Reply to {address} had the wrong address {message.address!r}; "
                        "does the OSCdef echo the right address?"
                    )
                    raise ValueError(msg)

                return message.params[1:]

    def ping(self, timeout: float = 5.0) -> None:
        """Ping SuperCollider."""
        try:
            response = self.request("/ping", timeout=timeout)
        except TimeoutError:
            msg = "Failed to ping (is SuperCollider booted?)"
            raise TimeoutError(msg) from None

        if response != ["success"]:
            msg = f"Unexpected response to /ping: {response!r}"
            raise ValueError(msg)

    def get_clock_state(self) -> ClockState:
        """Request state from SuperCollider and construct a ClockState from the response."""
        requested_at = time.monotonic()
        response = self.request("/state")
        return ClockState.from_message(response, requested_at, expiry=self._clock_state_timeout)

    def set_meter(self, upper: int, lower: int) -> float:
        """Set SC's meter from an `upper`/`lower` time signature.

        Request a change at the next bar, failing if one has already been requested (and still
        pending), or if we are requesting a meter change at a time in the past.
        """
        if upper <= 0:
            msg = "`upper` should be > 0"
            raise ValueError(msg)
        if lower <= 0:
            msg = "`lower` should be > 0"
            raise ValueError(msg)

        state = self.get_clock_state()

        # Prevent another meter change before the last change has materialised
        last = self._last_meter_change
        settle_beats = METER_SETTLE_SECONDS * state.beats_per_second
        pending_until = None if last is None else last.changed_at_beats + settle_beats
        if pending_until is not None and state.beats < pending_until:
            msg = f"meter change pending until beat {pending_until:.3f} (now {state.beats:.3f})"
            raise ExistingPendingMeterChangeError(msg)

        # Try to request the meter change from SC
        next_bar_beats = state.next_bar_beats()
        beats_per_bar = (upper / lower) * 4.0
        response = self.request("/set/beats_per_bar", beats_per_bar, next_bar_beats)
        match response:
            case ["ok", float(confirmed)]:
                if not math.isclose(confirmed, beats_per_bar, rel_tol=1e-6):
                    msg = f"SC scheduled {confirmed}, expected {beats_per_bar}"
                    raise ValueError(msg)
            case ["late", float(current_beats)]:
                msg = (
                    f"Meter change for beat {next_bar_beats} arrived late "
                    f"(SC was already at {current_beats})"
                )
                raise LateMeterChangeError(msg)
            case _:
                msg = f"Unexpected response: {response!r}"
                raise ValueError(msg)

        self._last_meter_change = Meter(upper, lower, next_bar_beats)

        return next_bar_beats

    @property
    def clock_state(self) -> ClockState:
        """Return a ClockState.

        Will cache for a very short interval for debouncing of multiple accessess of this attribute.
        """
        if self._cached_state is None or self._cached_state.is_stale():
            self._cached_state = self.get_clock_state()

        return self._cached_state

    def next_bar_beats(self, min_seconds: float = NEXT_BAR_LEAD_SECONDS) -> float:
        """Retrieve next_bar_beats from a fresh or recently-cached ClockState."""
        return self.clock_state.next_bar_beats(min_seconds)
