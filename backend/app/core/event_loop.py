"""
Event loop registry — captures the uvicorn asyncio loop at startup
so sync route handlers can schedule coroutines thread-safely.

Problem:
  FastAPI runs synchronous endpoint handlers in a ThreadPoolExecutor.
  From inside that thread, asyncio.get_event_loop() raises RuntimeError
  on Python 3.10+ because there is no running loop in the worker thread.
  asyncio.get_running_loop() also fails for the same reason.

Solution:
  Store a reference to the event loop during app lifespan startup (which
  runs in the event loop thread), then use run_coroutine_threadsafe()
  with that stored reference from any sync context.

Usage:
  from app.core.event_loop import get_main_loop

  loop = get_main_loop()
  if loop:
      asyncio.run_coroutine_threadsafe(coro, loop)
"""

import asyncio
from typing import Optional

_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called once during app startup to register the running event loop."""
    global _loop
    _loop = loop


def get_main_loop() -> Optional[asyncio.AbstractEventLoop]:
    """Returns the stored event loop, or None if not yet set."""
    return _loop
