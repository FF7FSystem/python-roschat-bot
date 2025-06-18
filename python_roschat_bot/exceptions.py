class RosChatBotError(Exception):
    """Base exception for RosChat bot errors."""


class AuthorizationError(RosChatBotError):
    """Raised when bot fails to authorize with the server."""


class BotConnectionError(RosChatBotError):
    """Raised when connection to server fails."""


class InvalidDataError(RosChatBotError):
    """Raised when data validation fails."""


class WebSocketPortError(RosChatBotError):
    """Raised when unable to retrieve WebSocket port from server configuration."""
