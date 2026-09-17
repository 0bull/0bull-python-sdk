[![0bull](https://0bull.net/images/brand/og-image.jpg)](https://0bull.net)

# 0bull Python SDK

A typed Python client for the [0bull API](https://docs.0bull.net): manage posting accounts,
publish videos, and control phones from Python. See [0bull.net](https://0bull.net) for the
product and [docs.0bull.net](https://docs.0bull.net) for the full API reference.

## Install

```bash
pip install 0bull
# or
uv add 0bull
```

The package is imported as `zerobull` and requires Python 3.10+.

## Authentication

Create a token at [0bull.net/settings/api-tokens](https://0bull.net/settings/api-tokens), scoped
to the abilities your code needs:

| Ability | Grants |
|---|---|
| `phones:read` | List phones, snapshots, OCR |
| `phones:control` | Tap, swipe, hotkey, type, runs |
| `accounts` | List, create, update, delete posting accounts |
| `submissions` | List, create, cancel, delete submissions; uploads |
| `billing` | Billing summary, rentals, phone count requests |

Pass the token explicitly or set `ZEROBULL_API_TOKEN`:

```python
from zerobull import ZeroBull

client = ZeroBull(api_token="...")
# or, with ZEROBULL_API_TOKEN set in the environment:
client = ZeroBull()
```

A request made with a token missing the required ability raises `PermissionDeniedError`.

## Quickstart (sync)

```python
from zerobull import ZeroBull

with ZeroBull() as client:
    phones = client.phones.list()
    print(phones[0].slot, phones[0].name)
```

## Quickstart (async)

```python
import asyncio
from zerobull import AsyncZeroBull


async def main() -> None:
    async with AsyncZeroBull() as client:
        phones = await client.phones.list()
        print(phones[0].slot, phones[0].name)


asyncio.run(main())
```

## Phones

Coordinates for `tap`, `swipe`, and `run_command`'s brightness `level` are 0-1 fractions of the
screen; `snapshot` and `ocr` accept an optional `width` between 120 and 2000. `hotkey` accepts
`home`, `app_switcher`, `control_center`, `notifications`, `back`, `run_shortcut`, `enter`,
`backspace`, `copy`, `cut`, `paste`, and `select_all`.

```python
phones = client.phones.list()
slot = phones[0].slot

jpeg: bytes = client.phones.snapshot(slot, width=600)
text: str = client.phones.ocr(slot)

client.phones.tap(slot, fx=0.5, fy=0.9)
client.phones.swipe(slot, fx1=0.5, fy1=0.8, fx2=0.5, fy2=0.2, steps=30)
client.phones.type(slot, "hello")
client.phones.hotkey(slot, "enter")
```

## Runs

Commands, macros, and agent tasks all queue a `Run`:

```python
run = client.phones.run_command(slot, "brightness", level=0.5)
run = client.phones.run_macro(slot, workflow="post-to-story", params={"caption": "hi"})
run = client.phones.run_agent(slot, "Open Settings and turn on Wi-Fi")

run = client.runs.wait(run, timeout=300)
print(run.status, run.result)

for run in client.runs.list(slot).iter_all():
    print(run.id, run.status)
```

`wait()` polls until the run reaches a terminal status (`succeeded`, `failed`, `cancelled`) and
raises `WaitTimeoutError` if `timeout` elapses first.

## Accounts and submissions

```python
from pathlib import Path

account = client.accounts.create(platform="tiktok", handle="@me", slot=slot)

submission = client.submissions.create(account_id=account.id, video=Path("clip.mp4"), caption="hi")
# or video_url="https://...", or upload_id from client.uploads.upload(...)

submission = client.submissions.wait(submission, timeout=900)
client.submissions.cancel(submission.id)
client.accounts.delete(account.id)

for account in client.accounts.list().iter_all():
    print(account.id, account.handle)
```

`submissions.create` takes exactly one of `video` (a local file, ≤200 MB, MP4/MOV), `video_url`,
or `upload_id`. `submissions.wait()` polls until a terminal status (`published`, `drafted`,
`failed`, `cancelled`).

`.list()` returns a `Page`; `iter_all()` walks every page, sync or async, without manual paging.

## Uploads

Upload a local file once and reuse the resulting id, for example to submit the same video to
several accounts:

```python
upload_id = client.uploads.upload("clip.mp4")
submission = client.submissions.create(account_id=account.id, upload_id=upload_id, caption="hi")
```

## Billing

```python
summary = client.billing.summary()
rental = client.billing.start_rental(accept_terms=True, phones=5, country="US")
change = client.billing.request_phone_count(accept_terms=True, add=2)
request = client.billing.get_request(change.request_id)
```

`accept_terms=True` confirms the caller has shown the user the
[terms](https://0bull.net/terms) and [privacy policy](https://0bull.net/privacy), including that
the rental renews monthly, before the charge is made.

## WebSocket

`client.socket()` returns a `Socket` (or `AsyncSocket`) exposing the same resource methods as the
REST client, over a connection that's authenticated and reconnected automatically:

```python
from zerobull import RunEvent

with client.socket() as socket:
    socket.phones.tap(slot, fx=0.5, fy=0.5)
    run = socket.phones.run_macro(slot, workflow="post-to-story")
    for event in socket.events():
        if isinstance(event, RunEvent) and event.run.id == run.id and event.run.is_terminal:
            break
```

```python
async with client.socket() as socket:
    phones = await socket.phones.list()
    async for event in socket.events():
        ...
```

`events()` yields `RunEvent`, `SubmissionEvent`, and `BillingRequestEvent`. A local file passed to
`submissions.create` over the socket is uploaded through a signed URL on the owning client's HTTP
transport first, then sent as `upload_id`. `user`, `session`, and any request carrying a local
file upload are REST-only and raise `NotImplementedError` on the socket.

On an unexpected disconnect, the socket reconnects with a fresh session URL and exponential
backoff, up to `max_reconnect_attempts`; calls in flight at the time of the disconnect raise
`SocketClosedError` rather than being resent. Use `socket.call(fun, data)` to invoke a fun the SDK
doesn't model yet; it gets the same error mapping as every other call.

## Errors

All exceptions subclass `ZeroBullError`.

| Condition | Exception |
|---|---|
| 400 | `BadRequestError` |
| 401 | `AuthenticationError` |
| 403 | `PermissionDeniedError` |
| 404 | `NotFoundError` |
| 409 | `ConflictError` |
| 422 | `ValidationError` (with `.errors`) |
| 429 | `RateLimitError` (after retries, with `.retry_after`) |
| 502, 503 | `UnavailableError` |
| ≥ 500 otherwise | `InternalServerError` |
| any other status | `APIStatusError` (base of all status errors) |
| network failure | `APIConnectionError` |
| request or call timeout | `APITimeoutError` |
| socket closed with calls in flight | `SocketClosedError` |
| `wait()` timeout | `WaitTimeoutError` |

```python
from zerobull import APIStatusError, ValidationError

try:
    client.submissions.create(
        account_id=account.id, video_url="https://example.com/missing.mp4", caption="hi"
    )
except ValidationError as e:
    print(e.errors)
except APIStatusError as e:
    print(e.status, e.message)
```

Arguments the SDK can validate locally, such as a missing `google_email` on a YouTube account,
raise `ValueError` before any request is sent; only a request that reaches the server can raise
`ValidationError` or another `APIStatusError`.

A REST `429` is retried automatically, honoring `Retry-After`, up to `max_retries` before
`RateLimitError` is raised. Nothing else is retried automatically.

## Configuration

`ZeroBull` / `AsyncZeroBull`:

| Option | Default | Environment |
|---|---|---|
| `api_token` | required | `ZEROBULL_API_TOKEN` |
| `base_url` | `https://0bull.net/api` | `ZEROBULL_BASE_URL` |
| `timeout` | 30s | |
| `max_retries` (REST `429`) | 2 | |
| `http_client` | none; an injected `httpx.Client` / `httpx.AsyncClient` | |

`client.socket()`:

| Option | Default |
|---|---|
| `call_timeout` | 60s |
| `auto_reconnect` | `True` |
| `max_reconnect_attempts` | 5 |
| `ping_interval` | 20s |

## Versioning and support

This SDK follows [semantic versioning](https://semver.org/). Before `1.0.0`, minor versions may
include breaking changes. See [CHANGELOG.md](CHANGELOG.md) for what changed in each release.

## Development

```bash
uv sync
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest
```

## License

MIT
