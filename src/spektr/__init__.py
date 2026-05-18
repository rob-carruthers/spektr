from pythonosc.udp_client import SimpleUDPClient
import random
import time


def main() -> None:
    client = SimpleUDPClient("127.0.0.1", 57120)

    notes = [220, 330, 440, 550]

    while True:
        client.send_message("/note", random.choice(notes))
        time.sleep(0.5)
