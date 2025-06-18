import json
import logging
import re
from collections.abc import Callable
import functools
from typing import Any, TypeVar, Iterable, Optional

from .enums import ServerEvents
from .schemas import Settings, EventOutcome, DataContent
from .exceptions import ConnectionError, InvalidDataError
from .socket_handler import SocketHandler
import requests

DEFAULT_LOGGER = logging.getLogger('roschat.bot')
COMMAND_REGEX = re.compile(r"^/\w+$")
F = TypeVar('F', bound=Callable)

class RosChatBot:
    """
    Main bot class for RosChat platform.
    
    This class provides functionality for creating and managing
    bots that can interact with RosChat server.
    """
    
    def __init__(
        self, 
        logger: Optional[logging.Logger] = None, 
        debug_socketio: bool = False,
        debug_engineio: bool = False
    ) -> None:
        self._settings = Settings()
        self.logger = logger or DEFAULT_LOGGER
        self._socket_handler = SocketHandler(
            credentials=self._settings.credentials,
            logger=self.logger,
            debug_socketio=debug_socketio,
            debug_engineio=debug_engineio
        )
        self.command_registry: dict[str, Callable] = {}
        self._button_registry: dict[str, Callable] = {}

    def connect(self) -> None:
        try:
            socket_url = self._get_socket_url()
            self._socket_handler.connect_to_server(socket_url, self._settings.socket_options)
            self._register_default_handlers()
            self._socket_handler.wait_for_authorization()
        except Exception as e:
            self.logger.exception(e)
            raise ConnectionError(e)

    @property
    def _webserver_config(self) -> dict:
        try:
            response = requests.get(f"{self._settings.base_url}/ajax/config.json", verify=False)
        except requests.exceptions.RequestException as e:
            self.logger.exception(e)
            raise
        else:
            return response.json()

    def _get_socket_url(self) -> str:
        self.logger.info("Get Roschat server port")
        web_sockets_port = self._webserver_config.get('webSocketsPortVer4', None)
        if web_sockets_port is None:
            raise ConnectionError("Couldn't get the value of the web socket from the web server configuration")
        return f"{self._settings.base_url}:{web_sockets_port}"

    def _register_default_handlers(self) -> None:
        # Register handlers because the bot implements the functionality of processing commands\ buttons.
        self._add_handler(ServerEvents.BOT_MESSAGE_EVENT, self._socket_handler.default_callback)
        self._add_handler(ServerEvents.BOT_BUTTON_EVENT, self._socket_handler.default_callback)

    def send_message(self, cid: int, data: str | dict, callback: Callable = None) -> None:
        # TODO think about validate incoming date by pydantic and create certain Model for each event (with custom dump function for dispatch->)
        params = {
            'cid': cid,
            'data': data if isinstance(data, str) else json.dumps(data)
        }

        self._socket_handler.dispatch_event(ServerEvents.SEND_BOT_MESSAGE, data=params, callback=callback)

    def mark_message_received(self, msg_id: int, callback: Callable = None) -> None:
        self._socket_handler.dispatch_event(ServerEvents.BOT_MESSAGE_RECEIVED, data={'id': msg_id}, callback=callback)

    def mark_message_watched(self, msg_id: int, callback: Callable = None) -> None:
        self._socket_handler.dispatch_event(ServerEvents.BOT_MESSAGE_WATCHED, data={'id': msg_id}, callback=callback)

    def message_delete(self, msg_id: int, callback: Callable = None) -> None:
        self._socket_handler.dispatch_event(ServerEvents.DELETE_BOT_MESSAGE, data={'id': msg_id}, callback=callback)

    def _set_keyboard(self, params: dict, callback: Callable = None) -> None:
        if not params.get('cid'):
            raise InvalidDataError("Required the cid field is not provided")
        if not params.get('action'):
            raise InvalidDataError("Required the action field is not provided")
        if not params.get('keyboard'):
            raise InvalidDataError("Required the keyboard field is not provided")

        self._socket_handler.dispatch_event(ServerEvents.SET_BOT_KEYBOARD, data=params, callback=callback)

    def turn_on_keyboard(self, cid: int, callback: Callable = None) -> None:
        param = {
            'cid': cid,
            'keyboard': self._keyboard_layer,
            'action': 'show'
        }
        self._set_keyboard(param, callback)

    def turn_off_keyboard(self, cid: int, callback: Callable = None) -> None:
        self.logger.warning("The command to hide the keyboard is not yet known.")
        param = {
            'cid': cid,
            'keyboard': self._keyboard_layer,
            'action': 'hide'
        }
        self._set_keyboard(param, callback)

    def _add_handler(self, event: ServerEvents, handler: Callable) -> None:
        self._socket_handler.register_handler(event, self.server_response_processing(handler, event))

    def message(self) -> Callable[[F], F]:
        def wrapper(handler: F) -> F:
            self._add_handler(ServerEvents.BOT_MESSAGE_EVENT, handler)
            self.logger.info("Message handler was added")
            return handler

        return wrapper

    def command(self, command: str) -> Callable[[F], F]:
        if not self.__extract_command(command):
            raise InvalidDataError(f"Command '{command}' is not valid")

        def wrapper(handler: F) -> F:
            self.command_registry[command] = handler
            self.logger.info(f"Command '{command}' was added")
            return handler

        return wrapper

    def button(self, button_name: str | Iterable[str]) -> Callable[[F], F]:

        names = (button_name,) if isinstance(button_name, str) else button_name

        def wrapper(handler: F) -> F:
            for name in names:
                self._button_registry[name] = handler
                self.logger.info(f"Button '{name}' was added")
            return handler

        return wrapper

    def start_polling(self) -> None:
        self._socket_handler.wait()

    def server_response_processing(self, func: Callable, event: ServerEvents) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                if not args or not isinstance(args[0], dict):
                    raise InvalidDataError(f"Server didn't get incoming data")

                data = dict(args[0])  # copy
                data["event"] = event
                processed_incoming = EventOutcome(**data)

                if event == ServerEvents.BOT_MESSAGE_EVENT:
                    if isinstance(processed_incoming.data, DataContent):
                        if processed_incoming.data.type == 'message-writing':
                            # The process of processing message changes should be implemented from the
                            # 'bot-message-change-event' events, but at the moment it is not implemented on the server side.
                            return

                        elif processed_incoming.data.type == 'text':
                            command = self.__extract_command(processed_incoming.data.text)
                            if command:
                                return self._dispatch_command(command, processed_incoming)

                elif event == ServerEvents.BOT_BUTTON_EVENT:
                    return self._dispatch_button(processed_incoming)

                return func(processed_incoming, self, **kwargs)

            except Exception as e:
                self.logger.exception(f"Error in handler for event '{event}': {e}")
                return None

        return wrapper

    def __extract_command(self, message: str) -> str | None:
        match = COMMAND_REGEX.match(message.strip())
        return None if not match else match.group(0)

    def _dispatch_command(self, command: str, event: EventOutcome) -> Any | None:
        command_handler = self.command_registry.get(command, None)
        if command_handler is not None and callable(command_handler):
            return command_handler(event, self)
        else:
            self.logger.warning(f"Command '{command}' is not registered")

    def _dispatch_button(self, server_incoming: EventOutcome) -> Any | None:
        if server_incoming.callback_data:
            button_handler = self._button_registry.get(server_incoming.callback_data, None)
            if button_handler is not None and callable(button_handler):
                return button_handler(server_incoming, self)
            else:
                self.logger.warning(f"Button '{server_incoming.callback_data}' is not registered")

    @property
    def _keyboard_layer(self) -> list[list[dict]]:

        keyboard_layer = []
        row = []

        for i, button_name in enumerate(self._button_registry):
            row.append({key: button_name for key in ('text', 'callbackData')})

            if (i + 1) % self._settings.keyboard_cols == 0:
                keyboard_layer.append(row)
                row = []

        if row:
            keyboard_layer.append(row)

        return keyboard_layer
