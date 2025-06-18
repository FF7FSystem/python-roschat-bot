"""
RosChat Bot Library
A Python library for creating bots for RosChat platform.
"""

from .bot import RosChatBot
from .enums import ServerEvents
from .exceptions import AuthorizationError
from .schemas import DataContent
from .schemas import EventOutcome
from .schemas import Settings

__all__ = [
    "RosChatBot",
    "Settings",
    "EventOutcome",
    "DataContent",
    "ServerEvents",
    "AuthorizationError",
]
