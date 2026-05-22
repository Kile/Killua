"""Context managers for test view / respond_to_view wiring."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable


@contextmanager
def respond_to_view(ctx: Any, callback: Callable[..., Any]):
    prev = ctx.respond_to_view
    ctx.respond_to_view = callback
    try:
        yield
    finally:
        ctx.respond_to_view = prev
