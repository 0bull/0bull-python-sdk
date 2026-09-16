# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added

- `ZeroBull` and `AsyncZeroBull` REST clients, and `Socket` and `AsyncSocket` WebSocket clients,
  with matching resource methods across all four surfaces.
- Accounts: list, get, create, update, delete.
- Submissions: list, get, create (local file, `video_url`, or `upload_id`), cancel, delete, and
  `wait()`.
- Uploads: signed upload URLs via `uploads.create()` and `uploads.upload()`.
- Phones: list, snapshot, OCR, tap, swipe, hotkey, type.
- Phone runs: commands, macros, agent runs; list, get, and `wait()`.
- Billing: summary, rentals, phone count requests, and billing request lookup.
- Phone-controller sessions and `client.socket()`, with automatic reconnects.
- Typed events (`RunEvent`, `SubmissionEvent`, `BillingRequestEvent`) via `socket.events()`.
- Pagination (`Page`, `AsyncPage`) with `iter_all()` across sync and async clients.
- A typed exception hierarchy mapping every documented REST and WebSocket error.
- `py.typed` marker; passes `mypy --strict`.
