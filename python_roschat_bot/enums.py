from enum import StrEnum


class ServerEvents(StrEnum):
    CONNECT = "connect"
    START_BOT = "start-bot"
    SEND_BOT_MESSAGE = "send-bot-message"
    BOT_MESSAGE_EVENT = "bot-message-event"
    BOT_MESSAGE_CHANGE_EVENT = "bot-message-change-event"
    BOT_MESSAGE_RECEIVED = "bot-message-received"
    BOT_MESSAGE_WATCHED = "bot-message-watched"
    DELETE_BOT_MESSAGE = "delete-bot-message"
    SET_BOT_KEYBOARD = "set-bot-keyboard"
    BOT_BUTTON_EVENT = "bot-button-event"
