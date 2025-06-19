import threading
from collections.abc import Callable
from logging import Logger

import requests
import socketio  # pylint: disable=import-error

from .enums import ServerEvents
from .exceptions import AuthorizationError


class SocketHandler(socketio.ClientNamespace):
    """Handles WebSocket connections to RosChat server."""

    def __init__(
        self,
        credentials: dict,
        logger: Logger,
        debug_socketio: bool = False,
        debug_engineio: bool = False,
    ) -> None:
        super().__init__(namespace="/")
        self.logger = logger
        self._credentials = credentials
        self._auth_event = threading.Event()

        http_session = requests.Session()
        http_session.verify = False

        self._sio = socketio.Client(
            reconnection_attempts=5,
            http_session=http_session,
            logger=logger if debug_socketio else debug_socketio,
            engineio_logger=logger if debug_engineio else debug_engineio,
        )
        self._sio.register_namespace(self)

    def on_connect(self, *args, **kwargs) -> None:
        self.logger.info(f"Connected to Server. Details: {args},{kwargs}")
        self.authorization(self._credentials, callback=self._authorization_callback)

    def on_connect_error(self, *args, **kwargs) -> None:
        self.logger.warning(
            f"Connection error. Details: {args},{kwargs}",
        )

    def on_disconnect(self, reason) -> None:
        self.logger.warning(f"The connection was terminated. Details: {reason}")

    def connect_to_server(self, socket_url: str, socket_options: dict) -> None:
        self.logger.info("Connecting to the server")
        self._sio.connect(socket_url, headers=socket_options)

    def authorization(self, credentials: dict, callback: Callable = None) -> None:
        self.logger.info("Authorization of the bot")
        self.dispatch_event(ServerEvents.START_BOT, data=credentials, callback=callback)

    def _authorization_callback(
        self, response: dict
    ) -> None:  # pylint: disable=unused-argument
        self._auth_event.set()

    def wait_for_authorization(self, timeout=5.0):
        self._auth_event.clear()
        if not self._auth_event.wait(timeout):
            raise AuthorizationError("Server didn't confirm authorization in time")
        self.logger.info("The authorization was successful")

    def dispatch_event(self, event: ServerEvents, data: dict, callback: Callable) -> None:
        self._sio.emit(event, data=data, callback=callback)

    def register_handler(self, event: ServerEvents, handler: Callable) -> None:
        self._sio.on(event, handler=handler)

    def wait(self) -> None:
        self._sio.wait()

    def default_callback(self, *arg, **kwargs) -> None:
        self.logger.info(f"Default callback function got back: {arg=},{kwargs=}")
