"""
RosChat Bot Library
A Python library for creating bots for RosChat platform.
"""

from .bot import RosChatBot
from .schemas import Settings, EventOutcome, DataContent
from .enums import ServerEvents
from .exceptions import AuthorizationError

__all__ = [
    "RosChatBot",
    "Settings",
    "EventOutcome",
    "DataContent",
    "ServerEvents",
    "AuthorizationError"
]