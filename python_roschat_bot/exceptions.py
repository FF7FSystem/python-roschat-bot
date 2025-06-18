class RosChatBotError(Exception):
    """Base exception for RosChat bot errors."""
    pass


class AuthorizationError(RosChatBotError):
    """Raised when bot fails to authorize with the server."""
    pass


class ConnectionError(RosChatBotError):
    """Raised when connection to server fails."""
    pass


class InvalidDataError(RosChatBotError):
    """Raised when data validation fails."""
    pass


class WebSocketPortError(RosChatBotError):
    """Raised when unable to retrieve WebSocket port from server configuration."""
    pass
