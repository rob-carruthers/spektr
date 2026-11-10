# ruff: noqa: D100, D103
from spektr.transport import Transport


def test_transport_creation_and_ping() -> None:
    Transport()
