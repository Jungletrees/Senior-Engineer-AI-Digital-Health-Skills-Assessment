"""Optional Chainlit step decorator.

The backend test suite does not install or run Chainlit. This wrapper keeps the
same call sites instrumentable in Chainlit while remaining a no-op elsewhere.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


def chainlit_step(name: str, step_type: str = "tool") -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    try:
        import chainlit as cl  # type: ignore[import-not-found]
    except Exception:
        cl = None

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        if cl is None:
            return fn
        try:
            return cl.step(name=name, type=step_type)(fn)  # type: ignore[no-any-return]
        except Exception:
            return fn

    return decorator
