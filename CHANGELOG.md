# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-17

### Added

- `ZeroBull` and `AsyncZeroBull` REST clients, and `Socket` and `AsyncSocket` WebSocket clients,
  with matching resource methods across all four surfaces.
- User: `user.get()` for the authenticated user (REST).
- Accounts: list, get, create, update, delete.
- Submissions: list, get, create (local file, `video_url`, or `upload_id`), cancel, delete, and
  `wait()`. Over the WebSocket, a local file is uploaded through a signed URL first.
- Uploads: signed upload URLs via `uploads.create()` and `uploads.upload()`.
- Phones: list, snapshot, OCR, tap, swipe, hotkey, type.
- Phone runs: commands, macros, agent runs; list, get, and `wait()`.
- Billing: summary, rentals, phone count requests, and billing request lookup.
- Phone-controller sessions and `client.socket()`, with concurrent calls and automatic reconnects.
- Typed events (`RunEvent`, `SubmissionEvent`, `BillingRequestEvent`) via `socket.events()`.
- `socket.call()` for WebSocket functions the SDK doesn't model yet.
- Pagination (`Page`, `AsyncPage`) with `iter_all()` across sync and async clients.
- A typed exception hierarchy mapping every documented REST and WebSocket error, with automatic
  retries for REST rate limits (`429`) honoring `Retry-After`.
- Configuration through arguments or `ZEROBULL_API_TOKEN` and `ZEROBULL_BASE_URL`.
- Runnable examples in `examples/`.
- Support for Python 3.10 through 3.14; `py.typed` marker; passes `mypy --strict`.

[0.1.0]: https://github.com/0bull/0bull-python-sdk/releases/tag/v0.1.0
