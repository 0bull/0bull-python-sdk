"""Synchronous and asynchronous phone access."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .._operations import phones
from .._resource import AsyncResource, SyncResource
from ..models.phones import CommandOp, Hotkey, MacroParams, Phone
from ..models.runs import Run


class Phones(SyncResource):
    """Synchronous phone access."""

    def list(self) -> list[Phone]:
        """List visible phones."""
        return self._execute(phones.list())

    def snapshot(self, slot: str, *, width: int | None = None) -> bytes:
        """Capture the phone screen as a JPEG; width must be 120-2000."""
        return self._execute(phones.snapshot(slot, width=width))

    def ocr(self, slot: str, *, width: int | None = None) -> str:
        """Read text from the screen; width must be 120-2000."""
        return self._execute(phones.ocr(slot, width=width))

    def tap(self, slot: str, *, fx: float, fy: float) -> None:
        """Tap at screen coordinates between 0 and 1."""
        return self._execute(phones.tap(slot, fx=fx, fy=fy))

    def swipe(
        self, slot: str, *, fx1: float, fy1: float, fx2: float, fy2: float, steps: int | None = None
    ) -> None:
        """Swipe between 0-1 coordinates with optional 1-500 steps."""
        return self._execute(phones.swipe(slot, fx1=fx1, fy1=fy1, fx2=fx2, fy2=fy2, steps=steps))

    def hotkey(self, slot: str, key: Hotkey) -> None:
        """Send a phone hotkey and wait for completion."""
        return self._execute(phones.hotkey(slot, key))

    def type(self, slot: str, text: str) -> None:
        """Type text and wait for completion."""
        return self._execute(phones.type(slot, text))

    def run_command(
        self,
        slot: str,
        op: CommandOp,
        *,
        text: str | None = None,
        url: str | None = None,
        level: float | None = None,
        on: bool | None = None,
    ) -> Run:
        """Queue a command with its required text, URL, 0-1 level, or on value."""
        return self._execute(phones.run_command(slot, op, text=text, url=url, level=level, on=on))

    def run_macro(
        self,
        slot: str,
        *,
        workflow: str | None = None,
        params: MacroParams | None = None,
        steps: Sequence[Mapping[str, object]] | None = None,
    ) -> Run:
        """Queue one workflow with scalar params or up to 200 action steps."""
        return self._execute(phones.run_macro(slot, workflow=workflow, params=params, steps=steps))

    def run_agent(self, slot: str, task: str) -> Run:
        """Queue an agent task containing 1-2000 characters."""
        return self._execute(phones.run_agent(slot, task))


class AsyncPhones(AsyncResource):
    """Asynchronous phone access."""

    async def list(self) -> list[Phone]:
        """List visible phones."""
        return await self._execute(phones.list())

    async def snapshot(self, slot: str, *, width: int | None = None) -> bytes:
        """Capture the phone screen as a JPEG; width must be 120-2000."""
        return await self._execute(phones.snapshot(slot, width=width))

    async def ocr(self, slot: str, *, width: int | None = None) -> str:
        """Read text from the screen; width must be 120-2000."""
        return await self._execute(phones.ocr(slot, width=width))

    async def tap(self, slot: str, *, fx: float, fy: float) -> None:
        """Tap at screen coordinates between 0 and 1."""
        return await self._execute(phones.tap(slot, fx=fx, fy=fy))

    async def swipe(
        self, slot: str, *, fx1: float, fy1: float, fx2: float, fy2: float, steps: int | None = None
    ) -> None:
        """Swipe between 0-1 coordinates with optional 1-500 steps."""
        return await self._execute(
            phones.swipe(slot, fx1=fx1, fy1=fy1, fx2=fx2, fy2=fy2, steps=steps)
        )

    async def hotkey(self, slot: str, key: Hotkey) -> None:
        """Send a phone hotkey and wait for completion."""
        return await self._execute(phones.hotkey(slot, key))

    async def type(self, slot: str, text: str) -> None:
        """Type text and wait for completion."""
        return await self._execute(phones.type(slot, text))

    async def run_command(
        self,
        slot: str,
        op: CommandOp,
        *,
        text: str | None = None,
        url: str | None = None,
        level: float | None = None,
        on: bool | None = None,
    ) -> Run:
        """Queue a command with its required text, URL, 0-1 level, or on value."""
        return await self._execute(
            phones.run_command(slot, op, text=text, url=url, level=level, on=on)
        )

    async def run_macro(
        self,
        slot: str,
        *,
        workflow: str | None = None,
        params: MacroParams | None = None,
        steps: Sequence[Mapping[str, object]] | None = None,
    ) -> Run:
        """Queue one workflow with scalar params or up to 200 action steps."""
        return await self._execute(
            phones.run_macro(slot, workflow=workflow, params=params, steps=steps)
        )

    async def run_agent(self, slot: str, task: str) -> Run:
        """Queue an agent task containing 1-2000 characters."""
        return await self._execute(phones.run_agent(slot, task))
