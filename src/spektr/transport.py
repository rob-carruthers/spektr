"""Transport, communication between Python and SuperCollider via OSC."""

import itertools
import time
from threading import Lock
from typing import NamedTuple, Self

from pythonosc.udp_client import SimpleUDPClient

SCLANG_PORT = 57120

type OscArg = int | float | str | bytes | bool | list[OscArg] | None


class ClockState(NamedTuple):
    """Holder of last-reported clock state of SuperCollider."""

    bar: int
    beats: float
    beats_per_second: float

    @classmethod
    def from_message(cls, params: list[OscArg]) -> Self:
        """Construct a ClockState from an OSC message response."""
        bar, beats, beats_per_second = params
        if not isinstance(bar, float):
            msg = "`bar` was not of type float."
            raise TypeError(msg)

        if not isinstance(beats, float):
            msg = "`beats` was not of type float."
            raise TypeError(msg)

        if not isinstance(beats_per_second, float):
            msg = "`beats_per_second` was not of type float."
            raise TypeError(msg)

        return cls(int(bar), beats, beats_per_second)

    @property
    def bpm(self) -> float:  # noqa: D102
        return self.beats_per_second * 60.0


class Transport:
    """Transport class holding an OSC SimpleUDPClient."""

    def __init__(self) -> None:
        """Initialize OSC client and test ping."""
        self.client = SimpleUDPClient("127.0.0.1", SCLANG_PORT)
        self._lock = Lock()
        self._ids = itertools.count(1)
        self.ping()

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
        response = self.request("/state")
        return ClockState.from_message(response)
