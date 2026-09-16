"""Async equivalent of sync_quickstart.py. Needs ZEROBULL_API_TOKEN."""

import asyncio

from zerobull import AsyncZeroBull


async def main() -> None:
    async with AsyncZeroBull() as client:
        phones = await client.phones.list()
        if not phones:
            print("No phones available")
            return
        phone = phones[0]
        print(f"{phone.slot}: {phone.name}")
        await client.phones.tap(phone.slot, fx=0.5, fy=0.5)


if __name__ == "__main__":
    asyncio.run(main())
