from threading import Lock

from pythonosc.udp_client import SimpleUDPClient

SC_PORT = 57120


class Transport:
    def __init__(self) -> None:
        self.client = SimpleUDPClient("127.0.0.1", SC_PORT)
        self._lock = Lock()

    def ping(self, timeout: float = 5.0) -> None:
        with self._lock:
            self.client.send_message("/ping", [])
            try:
                message = next(self.client.get_messages(timeout))
            except StopIteration:
                raise TimeoutError("SuperCollider did not respond to /ping")

        if message.address != "/ping" or message.params != ["success"]:
            raise ValueError("Unexpected response from /ping")


def main() -> None:
    transport = Transport()
    transport.ping()
