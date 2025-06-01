import json
import logging
from collections.abc import Callable
from logging import Logger
from typing import Any

import socketio
import requests
from enum import StrEnum

from pydantic import Field, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_LOGGER = logging.getLogger('roschat.bot')


class Settings(BaseSettings):
    token: str = Field(min_length=64)
    base_url: AnyHttpUrl = Field(...)
    bot_name: str = Field(min_length=1)
    query: None | str = Field(default='type-bot')
    reject_unauthorized: bool = Field(default=False, serialization_alias="rejectUnauthorized")

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    @property
    def socket_options(self) -> dict:
        return {'query': self.query, 'rejectUnauthorized': str(self.reject_unauthorized).lower()}

    @property
    def credentials(self) -> dict:
        return {'token': self.token, 'name': self.bot_name}


class ServerEvents(StrEnum):
    CONNECT = 'connect'
    START_BOT = 'start-bot'
    SEND_BOT_MESSAGE = 'send-bot-message'
    BOT_MESSAGE_EVENT = 'bot-message-event'
    BOT_MESSAGE_RECEIVED = 'bot-message-received'
    BOT_MESSAGE_WATCHED = 'bot-message-watched'
    DELETE_BOT_MESSAGE = 'delete-bot-message'
    SET_BOT_KEYBOARD = 'set-bot-keyboard'
    BOT_BUTTON_EVENT = 'bot-button-event'


class SocketHandler(socketio.ClientNamespace):

    def __init__(self, credentials: dict, logger: Logger, debug_mode: bool = False) -> None:
        super().__init__(namespace="*")
        self.logger = logger
        self._credentials = credentials
        http_session = requests.Session()
        http_session.verify = False
        self._sio = socketio.Client(http_session=http_session, logger=logger,
                                    engineio_logger=logger if debug_mode else debug_mode)

        self._sio.register_namespace(self)
        self._callbacks = {event.value: self.default_callback for event in ServerEvents}

    def on_connect(self) -> None:
        ...

    def on_connect_error(self, data) -> None:
        self.logger.warning(f"Connection error. Details: {data}", )

    def on_disconnect(self, reason) -> None:
        self.logger.warning(f"The connection was terminated. Details: {reason}")
        self._sio.disconnect()

    def registrate_connection(self, callback: Callable = None) -> None:
        self.logger.info("Connection registration")
        self._sio.on(ServerEvents.CONNECT, handler=self.default_callback if callback is None else callback)

    def connect_to_server(self, socket_url: str, socket_options: dict) -> None:
        self.logger.info("Connecting to the server")
        self._sio.connect(socket_url, headers=socket_options)
        self.authorization(self._credentials)

    def authorization(self, credentials: dict) -> None:
        self.logger.info("Authorization of the bot")
        event = ServerEvents.START_BOT.value
        self._sio.emit(event, data=credentials, callback=self._callbacks.get(event))

    def send_message(self, cid: int, data: str | dict):
        params = {
            'cid': cid,
            'data': data if isinstance(data, str) else json.dumps(data)
        }
        event = ServerEvents.SEND_BOT_MESSAGE.value
        self._sio.emit(ServerEvents.SEND_BOT_MESSAGE, data=params, callback=self._callbacks.get(event))

    def send_message_received(self, msg_id: int) -> None:
        event = ServerEvents.BOT_MESSAGE_RECEIVED.value
        self._sio.emit(event, data={'id': msg_id}, callback=self._callbacks.get(event))

    def send_message_watched(self, msg_id: int) -> None:
        event = ServerEvents.BOT_MESSAGE_WATCHED.value
        self._sio.emit(event, data={'id': msg_id},callback=self._callbacks.get(event))

    def delete_bot_message(self, msg_id):
        event = ServerEvents.DELETE_BOT_MESSAGE.value
        self._sio.emit(event, data={'id': msg_id},callback=self._callbacks.get(event))

    def set_bot_keyboard(self, data: dict) -> None:
        if not data.get('cid'):
            raise ValueError("Required the cid field is not provided")
        self._sio.emit(ServerEvents.SET_BOT_KEYBOARD, data=data)

    def processing_user_incoming(self, callback:Callable=None) -> None:
        # TODO change _callbacks to _handlers
        event = ServerEvents.BOT_MESSAGE_EVENT.value
        self._sio.on(event, handler=callback if callback else self._callbacks.get(event))

    def processing_button_event(self) -> None:
        # TODO change _callbacks to _handlers
        event = ServerEvents.BOT_BUTTON_EVENT.value
        self._sio.on(event, handler=self._callbacks.get(event))

    def wait(self) -> None:
        self._sio.wait()

    def default_callback(self, *arg, **kwargs) -> None:
        self.logger.info(f"Default callback function got back: {arg=},{kwargs=}")


class RosChatBot:

    def __init__(self, logger: Logger | None = None, debug_mode: bool = False) -> None:
        self._settings = Settings()
        self.logger = logger if logger else DEFAULT_LOGGER
        self.socket_handler = SocketHandler(credentials=self._settings.credentials, logger=self.logger,
                                            debug_mode=debug_mode)

    def connect(self, callback: Callable = None) -> None:

        try:
            socket_url = self.get_socket_url()
            self.socket_handler.registrate_connection(callback)
            self.socket_handler.connect_to_server(socket_url, self._settings.socket_options)

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

    def register_callback(self, event: ServerEvents, callback: Callable) -> None:
        self.socket_handler._callbacks[event.value] = callback
        self.logger.info(f"Callback for {event} was registered")

    def run_polling(self):
        self.socket_handler.wait()


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
    bot = RosChatBot(debug_mode=True)

    def incoming_handler(*args,**kwargs):
        print(f"incoming_handler({args=}, {kwargs=})")


    bot.connect()
    # bot.register_callback(ServerEvents.BOT_MESSAGE_EVENT, incoming_handler)
    bot.socket_handler.processing_button_event()
    bot.socket_handler.processing_user_incoming(incoming_handler)
    # bot.connect()
    bot.run_polling()
    print()
