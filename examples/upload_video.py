"""Upload a local video and print its upload id.

Needs ZEROBULL_API_TOKEN. Usage: python upload_video.py <path-to-video>
"""

import sys

from zerobull import ZeroBull


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python upload_video.py <path-to-video>")
        raise SystemExit(1)
    with ZeroBull() as client:
        upload_id = client.uploads.upload(sys.argv[1])
        print(upload_id)


if __name__ == "__main__":
    main()
