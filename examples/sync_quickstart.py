"""List phones and tap the first one. Needs ZEROBULL_API_TOKEN."""

from zerobull import ZeroBull


def main() -> None:
    with ZeroBull() as client:
        phones = client.phones.list()
        if not phones:
            print("No phones available")
            return
        phone = phones[0]
        print(f"{phone.slot}: {phone.name}")
        client.phones.tap(phone.slot, fx=0.5, fy=0.5)


if __name__ == "__main__":
    main()
