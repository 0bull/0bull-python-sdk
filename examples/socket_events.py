"""Run a macro over the WebSocket and wait for it to finish via events.

Needs ZEROBULL_API_TOKEN.
"""

from zerobull import RunEvent, ZeroBull


def main() -> None:
    with ZeroBull() as client:
        phones = client.phones.list()
        if not phones:
            print("No phones available")
            return
        slot = phones[0].slot
        with client.socket() as socket:
            run = socket.phones.run_macro(slot, workflow="post-to-story")
            print(f"started run {run.id}")
            for event in socket.events():
                if isinstance(event, RunEvent) and event.run.id == run.id and event.run.is_terminal:
                    print(f"run {event.run.id}: {event.run.status}")
                    break


if __name__ == "__main__":
    main()
