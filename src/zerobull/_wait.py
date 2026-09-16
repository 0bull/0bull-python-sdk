"""Deadline-bounded polling helpers."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from ._errors import WaitTimeoutError

T = TypeVar("T")


def wait_until(
    fetch: Callable[[], T],
    done: Callable[[T], bool],
    *,
    interval: float,
    timeout: float,
    what: str,
    sleep: Callable[[float], None] | None = None,
) -> T:
    """Poll until done or raise WaitTimeoutError at the deadline."""
    deadline = time.monotonic() + timeout
    sleeper = sleep or time.sleep
    while True:
        value = fetch()
        if done(value):
            return value
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise WaitTimeoutError(f"Timed out waiting for {what}")
        sleeper(min(interval, remaining))


async def await_until(
    fetch: Callable[[], Awaitable[T]],
    done: Callable[[T], bool],
    *,
    interval: float,
    timeout: float,
    what: str,
    sleep: Callable[[float], Awaitable[None]] | None = None,
) -> T:
    """Asynchronously poll until done or the deadline expires."""
    deadline = time.monotonic() + timeout
    sleeper = sleep or asyncio.sleep
    while True:
        value = await fetch()
        if done(value):
            return value
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise WaitTimeoutError(f"Timed out waiting for {what}")
        await sleeper(min(interval, remaining))
