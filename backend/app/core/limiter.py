"""
Rate limiter singleton — placed in a standalone module to prevent circular imports.

Import this in any endpoint module that needs per-route rate limiting:
    from app.core.limiter import limiter
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
