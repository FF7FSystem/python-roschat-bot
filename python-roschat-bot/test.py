import logging.config
import urllib3
from bot import RosChatBot
from schemas import EventOutcome


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
bot = RosChatBot(debug_socketio=True, debug_engineio=True)
bot.connect()


@bot.command('/test')
def command_custom_handler(incoming: EventOutcome, bot: RosChatBot) -> None:
    msg = f"Command '{incoming.data.text}' was executed"
    bot.send_message(incoming.cid, msg)


@bot.button(["test", "test1", "test2", "test3", "test4", "test5", "test6", "test7", "test8"])
def button_custom_handler(incoming: EventOutcome, bot: RosChatBot) -> None:
    msg = f"Button '{incoming.callback_data}' was pushed"
    bot.send_message(incoming.cid, msg)


@bot.command('/start')
def handle_start_command(incoming: EventOutcome, bot: RosChatBot) -> None:
    bot.turn_on_keyboard(incoming.cid, lambda x: print(x))
    bot.send_message(incoming.cid, f"Registered commands: {"".join([f"\n {key}" for key in bot.command_registry])}")


@bot.command('/keyboard_refresh')
def handle_keyboard_refresh_command(incoming: EventOutcome, bot: RosChatBot) -> None:
    bot.turn_on_keyboard(incoming.cid, lambda x: print(x))

# TODO that it will be not important the order of registration handlers and connection to server
@bot.message()
def incoming_handler(incoming: EventOutcome, bot: RosChatBot):
    msg = f"Message '{incoming.data.text}' was received from cid {incoming.cid}"
    bot.send_message(incoming.cid, msg)


bot.start_polling()