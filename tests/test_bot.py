import pytest
from unittest.mock import Mock, patch
from python_roschat_bot import RosChatBot
from python_roschat_bot.enums import ServerEvents
from python_roschat_bot.schemas import EventOutcome, DataContent, Settings


class TestRosChatBot:
    """Test cases for RosChatBot class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock Settings to avoid validation errors in tests
        patcher_settings = patch('python_roschat_bot.bot.Settings')
        patcher_env = patch('python_roschat_bot.bot.RosChatBot._resolve_env_file', return_value='tests/.env')
        self.addCleanup = getattr(self, 'addCleanup', lambda f: None)  # for pytest compatibility
        self.mock_settings = patcher_settings.start()
        self.mock_env = patcher_env.start()
        self.addCleanup(patcher_settings.stop)
        self.addCleanup(patcher_env.stop)

        mock_settings_instance = Mock()
        mock_settings_instance.token = "test_token_64_characters_long_for_testing_purposes_only"
        mock_settings_instance.base_url = "https://test.example.com"
        mock_settings_instance.bot_name = "TestBot"
        mock_settings_instance.credentials = {"token": "test_token", "name": "TestBot"}
        mock_settings_instance.socket_options = {"query": "type-bot", "rejectUnauthorized": "false"}
        mock_settings_instance.keyboard_cols = 3
        self.mock_settings.return_value = mock_settings_instance

        self.bot = RosChatBot()

    def test_bot_initialization(self):
        """Test bot initialization."""
        assert self.bot is not None
        assert hasattr(self.bot, 'command_registry')
        assert hasattr(self.bot, '_button_registry')
        assert isinstance(self.bot.command_registry, dict)
        assert isinstance(self.bot._button_registry, dict)

    def test_command_decorator(self):
        """Test command decorator registration."""

        @self.bot.command('/test')
        def test_handler(incoming, bot):
            return "test"

        assert '/test' in self.bot.command_registry
        assert self.bot.command_registry['/test'] == test_handler

    def test_button_decorator(self):
        """Test button decorator registration."""

        @self.bot.button('test_button')
        def test_handler(incoming, bot):
            return "test"

        assert 'test_button' in self.bot._button_registry
        assert self.bot._button_registry['test_button'] == test_handler

    def test_message_decorator(self):
        """Test message decorator registration."""

        @self.bot.message()
        def test_handler(incoming, bot):
            return "test"

        # Message handlers are registered internally, so we just check no error
        assert True

    def test_extract_command_valid(self):
        """Test command extraction with valid commands."""
        assert self.bot._RosChatBot__extract_command('/start') == '/start'
        assert self.bot._RosChatBot__extract_command('/help') == '/help'
        assert self.bot._RosChatBot__extract_command('/test_command') == '/test_command'

    def test_extract_command_invalid(self):
        """Test command extraction with invalid commands."""
        assert self.bot._RosChatBot__extract_command('start') is None
        assert self.bot._RosChatBot__extract_command('help') is None
        assert self.bot._RosChatBot__extract_command('') is None
        assert self.bot._RosChatBot__extract_command('not_a_command') is None

    def test_keyboard_layer_generation(self):
        """Test keyboard layer generation."""

        # Add some buttons
        @self.bot.button('button1')
        def handler1(incoming, bot):
            pass

        @self.bot.button('button2')
        def handler2(incoming, bot):
            pass

        @self.bot.button('button3')
        def handler3(incoming, bot):
            pass

        keyboard = self.bot._keyboard_layer
        assert isinstance(keyboard, list)
        assert len(keyboard) > 0
        assert all(isinstance(row, list) for row in keyboard)
        assert all(isinstance(button, dict) for row in keyboard for button in row)

    @patch('python_roschat_bot.bot.requests.get')
    def test_webserver_config(self, mock_get):
        """Test webserver config retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {"webSocketsPortVer4": "8080"}
        mock_get.return_value = mock_response

        config = self.bot._webserver_config
        assert config == {"webSocketsPortVer4": "8080"}

    @patch('python_roschat_bot.bot.requests.get')
    def test_get_socket_url(self, mock_get):
        """Test socket URL generation."""
        mock_response = Mock()
        mock_response.json.return_value = {"webSocketsPortVer4": "8080"}
        mock_get.return_value = mock_response

        url = self.bot._get_socket_url()
        assert "8080" in url


class TestEventOutcome:
    """Test cases for EventOutcome schema."""

    def test_event_outcome_creation(self):
        """Test EventOutcome object creation."""
        data = {
            "cid": 123,
            "id": 456,
            "event": ServerEvents.BOT_MESSAGE_EVENT,
            "data": {"type": "text", "text": "Hello"}
        }

        event = EventOutcome(**data)
        assert event.cid == 123
        assert event.id == 456
        assert event.event == ServerEvents.BOT_MESSAGE_EVENT
        assert isinstance(event.data, DataContent)
        assert event.data.type == "text"
        assert event.data.text == "Hello"


class TestDataContent:
    """Test cases for DataContent schema."""

    def test_data_content_creation(self):
        """Test DataContent object creation."""
        data = DataContent(type="text", text="Hello world")
        assert data.type == "text"
        assert data.text == "Hello world"
        assert isinstance(data.entities, list)
