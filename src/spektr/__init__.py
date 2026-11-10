import itertools
import time
from threading import Lock

from pythonosc.udp_client import SimpleUDPClient

SC_PORT = 57120


class Transport:
    def __init__(self) -> None:
        self.client = SimpleUDPClient("127.0.0.1", SC_PORT)
        self._lock = Lock()
        self._ids = itertools.count(1)

    def request(self, address: str, *args, timeout: float = 0.1):
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
                    raise TimeoutError(error_msg)

                if not message.params or message.params[0] != request_id:
                    continue  # stale or unrelated reply

                if message.address != address:
                    raise ValueError(
                        f"Reply to {address} had the wrong address {message.address!r}; "
                        "does the OSCdef echo the right address?"
                    )

                return message.params[1:]

    def ping(self, timeout: float = 5.0) -> None:
        response = self.request("/ping", timeout=timeout)
        if response != ["success"]:
            raise ValueError(f"Unexpected response to /ping: {response!r}")


def main() -> None:
    transport = Transport()
    transport.ping()
