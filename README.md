# Python RosChat Bot

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A modern Python library for creating bots for the RosChat platform. This library provides a simple and intuitive API for building interactive chatbots with support for commands, message handlers, and custom keyboards.

## Features

- 🚀 **Easy to use** - Simple decorator-based API
- 🔧 **Type-safe** - Full type hints and Pydantic validation
- 🎯 **Command system** - Built-in command handling with regex validation
- ⌨️ **Custom keyboards** - Dynamic keyboard generation and management
- 📨 **Message handling** - Flexible message processing system
- 🔄 **WebSocket support** - Real-time communication with RosChat server
- 🛡️ **Error handling** - Comprehensive exception hierarchy
- 📝 **Logging** - Built-in logging with configurable levels

## Installation

### From PyPI (when published)
```bash
pip install python-roschat-bot
```

### From source
```bash
git clone https://github.com/yourusername/python-roschat-bot.git
cd python-roschat-bot
pip install -e .
```

## Quick Start

### 1. Environment Configuration

First, create a `.env` file in your project root with the following configuration:

```bash
# Copy the example file
cp .env.example .env
```

Then edit `.env` with your bot credentials:

```env
TOKEN=your_bot_token_here_minimum_64_characters_long
BASE_URL=https://your-roschat-server.com
BOT_NAME=YourBotName
QUERY=type-bot
REJECT_UNAUTHORIZED=false
KEYBOARD_COLS=3
```

### 2. Basic Bot Setup

```python
import logging
from python_roschat_bot import RosChatBot, EventOutcome

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the bot
bot = RosChatBot(logger=logger)

# Connect to the server (REQUIRED before registering handlers)
bot.connect()

# Register your handlers here...

# Start the bot (REQUIRED to begin processing messages)
bot.start_polling()
```

## Core Concepts

### Handler Functions Structure

All handler functions must follow this structure:
```python
def your_handler(incoming: EventOutcome, bot: RosChatBot) -> None:
    # Your logic here
    pass
```

### Decorators

The library provides three main decorators for different types of interactions:

#### 1. Command Handler (`@bot.command`)

Handles slash commands (e.g., `/start`, `/help`):

```python
@bot.command('/start')
def handle_start_command(incoming: EventOutcome, bot: RosChatBot) -> None:
    bot.send_message(incoming.cid, "Welcome! Use /help for available commands.")

@bot.command('/help')
def handle_help_command(incoming: EventOutcome, bot: RosChatBot) -> None:
    help_text = """
Available commands:
/start - Start the bot
/help - Show this help message
/keyboard - Show custom keyboard
    """
    bot.send_message(incoming.cid, help_text)
```

#### 2. Message Handler (`@bot.message`)

Handles all incoming messages (except commands):

```python
@bot.message()
def handle_all_messages(incoming: EventOutcome, bot: RosChatBot) -> None:
    if incoming.data and incoming.data.text:
        bot.send_message(incoming.cid, f"You said: {incoming.data.text}")
```

#### 3. Button Handler (`@bot.button`)

Handles custom keyboard button presses:

```python
@bot.button(['option1', 'option2', 'option3'])
def handle_button_press(incoming: EventOutcome, bot: RosChatBot) -> None:
    button_name = incoming.callback_data
    bot.send_message(incoming.cid, f"You pressed: {button_name}")
```

## Bot Methods

### Message Operations

#### `bot.send_message(cid: int, data: str | dict, callback: Callable = None)`
Sends a message to a specific chat.

```python
# Send text message
bot.send_message(incoming.cid, "Hello, world!")

# Send structured data
bot.send_message(incoming.cid, {
    "type": "text",
    "content": "Formatted message"
})
```

#### `bot.mark_message_received(msg_id: int, callback: Callable = None)`
Marks a message as received (read receipt).

```python
bot.mark_message_received(incoming.id)
```

#### `bot.mark_message_watched(msg_id: int, callback: Callable = None)`
Marks a message as watched (seen receipt).

```python
bot.mark_message_watched(incoming.id)
```

#### `bot.message_delete(msg_id: int, callback: Callable = None)`
Deletes a specific message.

```python
bot.message_delete(incoming.id)
```

### Keyboard Operations

#### `bot.turn_on_keyboard(cid: int, callback: Callable = None)`
Shows the custom keyboard for a chat.

```python
@bot.command('/keyboard')
def show_keyboard(incoming: EventOutcome, bot: RosChatBot) -> None:
    bot.turn_on_keyboard(incoming.cid)
    bot.send_message(incoming.cid, "Keyboard activated!")
```

#### `bot.turn_off_keyboard(cid: int, callback: Callable = None)`
Hides the custom keyboard for a chat.

```python
@bot.command('/hide_keyboard')
def hide_keyboard(incoming: EventOutcome, bot: RosChatBot) -> None:
    bot.turn_off_keyboard(incoming.cid)
    bot.send_message(incoming.cid, "Keyboard hidden!")
```

## Complete Example

```python
import logging
from python_roschat_bot import RosChatBot, EventOutcome

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot
bot = RosChatBot(logger=logger)

# Connect to server (REQUIRED)
bot.connect()

# Command handlers
@bot.command('/start')
def start_command(incoming: EventOutcome, bot: RosChatBot) -> None:
    bot.send_message(incoming.cid, "Welcome! I'm your RosChat bot.")
    bot.turn_on_keyboard(incoming.cid)

@bot.command('/help')
def help_command(incoming: EventOutcome, bot: RosChatBot) -> None:
    help_text = """
Available commands:
/start - Start the bot and show keyboard
/help - Show this help message
/status - Show bot status

Available buttons:
- Info: Get bot information
- Settings: Bot settings
- Contact: Contact support
    """
    bot.send_message(incoming.cid, help_text)

@bot.command('/status')
def status_command(incoming: EventOutcome, bot: RosChatBot) -> None:
    status = f"""
Bot Status:
- Connected: ✅
- Commands registered: {len(bot.command_registry)}
- Buttons registered: {len(bot._button_registry)}
    """
    bot.send_message(incoming.cid, status)

# Button handlers
@bot.button(['info', 'settings', 'contact'])
def handle_buttons(incoming: EventOutcome, bot: RosChatBot) -> None:
    button = incoming.callback_data
    
    if button == 'info':
        bot.send_message(incoming.cid, "I'm a RosChat bot created with python-roschat-bot library!")
    elif button == 'settings':
        bot.send_message(incoming.cid, "Settings panel (not implemented yet)")
    elif button == 'contact':
        bot.send_message(incoming.cid, "Contact: support@example.com")

# Message handler (handles all non-command messages)
@bot.message()
def handle_messages(incoming: EventOutcome, bot: RosChatBot) -> None:
    if incoming.data and incoming.data.text:
        # Echo the message back
        bot.send_message(incoming.cid, f"You said: {incoming.data.text}")
        
        # Mark as received
        if incoming.id:
            bot.mark_message_received(incoming.id)

# Start the bot (REQUIRED)
bot.start_polling()
```

## Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `TOKEN` | Yes | Bot authentication token (min 64 chars) | - |
| `BASE_URL` | Yes | RosChat server base URL | - |
| `BOT_NAME` | Yes | Bot display name | - |
| `QUERY` | No | Socket query parameter | `type-bot` |
| `REJECT_UNAUTHORIZED` | No | Reject unauthorized connections | `false` |
| `KEYBOARD_COLS` | No | Number of columns in keyboard | `3` |

### Advanced Configuration

```python
from python_roschat_bot import RosChatBot

# Initialize with debug options
bot = RosChatBot(
    logger=my_logger,
    debug_socketio=True,  # Enable Socket.IO debug logging
    debug_engineio=True   # Enable Engine.IO debug logging
)
```

## Error Handling

The library provides a comprehensive exception hierarchy:

```python
from python_roschat_bot import (
    RosChatBotError,
    AuthorizationError,
    BotConnectionError,
    InvalidDataError,
    WebSocketPortError
)

try:
    bot.connect()
except AuthorizationError as e:
    print(f"Authorization failed: {e}")
except BotConnectionError as e:
    print(f"Connection failed: {e}")
except WebSocketPortError as e:
    print(f"WebSocket port error: {e}")
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black python_roschat_bot/
flake8 python_roschat_bot/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/yourusername/python-roschat-bot/issues) page
2. Create a new issue with detailed description
3. Contact: your-email@example.com

## Changelog

### v0.1.0
- Initial release
- Basic bot functionality
- Command, message, and button handlers
- Custom keyboard support
- WebSocket communication
- Pydantic validation 

## Providing the .env file for the library

The RosChatBot library requires a `.env` file with configuration variables. You can provide this file in one of the following ways:

1. **Pass an absolute path via the constructor:**
   
   ```python
   bot = RosChatBot(env_file_path="/absolute/path/to/.env")
   ```
   The path must be absolute. Relative paths are not supported.

2. **Set the environment variable `ROSCHAT_ENV_FILE_PATH`:**
   
   On Linux/macOS:
   ```bash
   export ROSCHAT_ENV_FILE_PATH=/absolute/path/to/.env
   ```
   On Windows:
   ```cmd
   set ROSCHAT_ENV_FILE_PATH=C:\absolute\path\to\.env
   ```
   The value must be an absolute path.

3. **Place a `.env` file next to the script being run:**
   
   If neither of the above is provided, the library will look for a `.env` file in the same directory as the script you are running.

If the `.env` file is not found using any of these methods, the library will raise a `FileNotFoundError` with a descriptive message.

**Note:** Relative paths are not supported for the `.env` file. Always use absolute paths when specifying the file location explicitly. 