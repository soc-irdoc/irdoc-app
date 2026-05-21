"""
Shared slowapi Limiter instance.

Import from here in both main.py (to attach to app.state) and any route
module that needs @limiter.limit — avoids circular imports through app.main.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
