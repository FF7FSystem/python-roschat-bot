import json
import logging
import threading
from collections.abc import Callable
import functools
from logging import Logger
from typing import Any
import re

from enums import ServerEvents
from schemas import Settings, EventOutcome, DataContent
import socketio
import requests
from exceptions import AuthorizationError

DEFAULT_LOGGER = logging.getLogger('roschat.bot')
COMMAND_REGEX = re.compile(r"^/\w+$")


class SocketHandler(socketio.ClientNamespace):

    def __init__(self, credentials: dict, logger: Logger, debug_socketio: bool, debug_engineio: bool) -> None:
        super().__init__(namespace="/")
        self.logger = logger
        self._credentials = credentials
        http_session = requests.Session()
        http_session.verify = False
        self._sio = socketio.Client(reconnection_attempts=5,
                                    http_session=http_session,
                                    logger=logger if debug_socketio else debug_engineio,
                                    engineio_logger=logger if debug_engineio else debug_engineio)

        self._sio.register_namespace(self)
        self._auth_event = threading.Event()

    def on_connect(self, *args, **kwargs) -> None:
        self.logger.info(f"Connected to Server. Details: {args},{kwargs}")
        self.authorization(self._credentials, callback=self._authorization_callback)

    def on_connect_error(self, *args, **kwargs) -> None:
        self.logger.warning(f"Connection error. Details: {args},{kwargs}", )

    def on_disconnect(self, reason) -> None:
        self.logger.warning(f"The connection was terminated. Details: {reason}")
        self._sio.disconnect()

    def connect_to_server(self, socket_url: str, socket_options: dict) -> None:
        self.logger.info("Connecting to the server")
        self._sio.connect(socket_url, headers=socket_options)

    def authorization(self, credentials: dict, callback: Callable = None) -> None:
        self.logger.info("Authorization of the bot")
        self.dispatch_event(ServerEvents.START_BOT, data=credentials, callback=callback)

    def _authorization_callback(self, response: dict) -> None:
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


class RosChatBot:

    def __init__(self, logger: Logger | None = None, debug_socketio: bool = False,
                 debug_engineio: bool = False) -> None:
        self._settings = Settings()
        self.logger = logger if logger else DEFAULT_LOGGER
        self._socket_handler = SocketHandler(credentials=self._settings.credentials,
                                             logger=self.logger,
                                             debug_socketio=debug_socketio,
                                             debug_engineio=debug_engineio)
        self._command_registry = dict()
        self._button_registry = dict()

    def connect(self) -> None:
        try:
            socket_url = self.get_socket_url()
            self._socket_handler.connect_to_server(socket_url, self._settings.socket_options)
            self._register_default_handlers()
            self._socket_handler.wait_for_authorization()
        except Exception as e:
            self.logger.exception(e)
            raise

    @property
    def _webserver_config(self) -> dict:
        try:
            response = requests.get(f"{self._settings.base_url}/ajax/config.json", verify=False)
        except requests.exceptions.RequestException as e:
            self.logger.exception(e)
            raise
        else:
            return response.json()

    def get_socket_url(self) -> str:
        self.logger.info("Get Roschat server port")
        web_sockets_port = self._webserver_config.get('webSocketsPortVer4', None)
        if web_sockets_port is None:
            raise ValueError("Couldn't get the value of the web socket from the web server configuration")
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
            raise ValueError("Required the cid field is not provided")
        if not params.get('action'):
            raise ValueError("Required the action field is not provided")
        if not params.get('keyboard'):
            raise ValueError("Required the keyboard field is not provided")

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

    def add_msg_handler(self, handler: Callable) -> None:
        self._add_handler(ServerEvents.BOT_MESSAGE_EVENT, handler)

    def add_command(self, command: str, handler: Callable) -> None:
        if not self.__extract_command(command):
            raise ValueError(f"Command '{command}' is not valid")

        self._command_registry[command] = handler
        self.logger.info(f"Command '{command}' was added")

    def add_button(self, button_name: str, handler: Callable) -> None:
        self._button_registry[button_name] = handler
        self.logger.info(f"Button '{button_name}' was added")

    def run_polling(self):
        self._socket_handler.wait()

    def server_response_processing(self, func: Callable, event: ServerEvents) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                if not args or not isinstance(args[0], dict):
                    raise ValueError(f"Server didn't get incoming data")

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
        command_handler = self._command_registry.get(command, None)
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
    def _keyboard_layer(self) -> list:
        keyboard_layer = []
        for button_name in self._button_registry:
            keyboard_layer.append({key: button_name for key in ('text', 'callbackData')})
        return [keyboard_layer]


if __name__ == "__main__":
    import logging.config
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
        },
        "loggers": {
            "roschat.bot": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(LOGGING_CONFIG)
    bot = RosChatBot(debug_socketio=True)


    def incoming_handler(incoming: EventOutcome, bot: RosChatBot):
        msg = f"Message '{incoming.data.text}' was received from cid {incoming.cid}"
        bot.send_message(incoming.cid, msg)


    def command_custom_handler(incoming: EventOutcome, bot: RosChatBot) -> None:
        msg = f"Command '{incoming.data.text}' was executed"
        bot.send_message(incoming.cid, msg)


    def button_custom_handler(incoming: EventOutcome, bot: RosChatBot) -> None:
        msg = f"Button '{incoming.callback_data}' was pushed"
        bot.send_message(incoming.cid, msg)


    def handle_start_command(incoming: EventOutcome, bot: RosChatBot) -> None:
        msg = f"Command '{incoming.data.text}' was executed"
        bot.turn_on_keyboard(incoming.cid, lambda x: print(x))
        bot.send_message(incoming.cid, msg)


    bot.connect()
    bot.add_command('/test', command_custom_handler)
    bot.add_command('/start', handle_start_command)
    bot.add_command('/keyboard_refresh', handle_start_command)
    bot.add_button('test', button_custom_handler)
    bot.add_button('test2', button_custom_handler)
    bot.add_button('test3', button_custom_handler)
    bot.add_button('test4', button_custom_handler)
    bot.add_button('test5', button_custom_handler)
    bot.add_button('test6', button_custom_handler)
    bot.add_button('test7', button_custom_handler)
    bot.add_button('test8', button_custom_handler)

    bot.add_msg_handler(incoming_handler)

    bot.run_polling()
    # print()
