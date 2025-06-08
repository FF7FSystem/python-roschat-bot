from typing import Any

from pydantic import Field, AnyHttpUrl, BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
from enums import ServerEvents


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


class DataContent(BaseModel):
    type: str | None = Field(default=None)
    text: str | None = Field(default=None)
    entities: list = Field(default_factory=list)


class EventOutcome(BaseModel):
    event: ServerEvents | None = Field(default=None)
    id: int | None = Field(default=None)
    cid: int
    cid_type: str | None = Field(default=None, alias='cidType')
    sender_id: int = Field(default=None, alias='senderId')
    type: str | None = Field(default=None)
    data: DataContent | None = Field(default=None)
    data_type: str | None = Field(default=None, alias='dataType')
    callback_data: str | None = Field(default=None, alias='callbackData')

    @field_validator('data', mode='before')
    @classmethod
    def parse_data(cls, value: Any) -> dict | Any:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed
            except json.JSONDecodeError:
                return {"text": value, "type": 'text'}

        return value
