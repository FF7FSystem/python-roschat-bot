import json
from typing import Any
from typing import Optional

from pydantic import AnyHttpUrl
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from .enums import ServerEvents


class Settings(BaseSettings):
    token: str = Field(min_length=64, description="Bot authentication token")
    base_url: AnyHttpUrl = Field(..., description="RosChat server base URL")
    bot_name: str = Field(min_length=1, description="Bot display name")
    query: Optional[str] = Field(default="type-bot", description="Socket query parameter")
    reject_unauthorized: bool = Field(
        default=False,
        serialization_alias="rejectUnauthorized",
        description="Whether to reject unauthorized connections",
    )
    keyboard_cols: int = Field(
        default=3, gt=0, description="Number of columns in keyboard layout"
    )

    model_config = SettingsConfigDict(
        env_file="../ examples/.env", env_file_encoding="utf-8", case_sensitive=False
    )

    @property
    def socket_options(self) -> dict:
        return {
            "query": self.query,
            "rejectUnauthorized": str(self.reject_unauthorized).lower(),
        }

    @property
    def credentials(self) -> dict:
        return {"token": self.token, "name": self.bot_name}


class DataContent(BaseModel):
    type: str | None = Field(default=None)
    text: str | None = Field(default=None)
    entities: list = Field(default_factory=list)


class EventOutcome(BaseModel):
    event: ServerEvents | None = Field(default=None)
    id: int | None = Field(default=None)
    cid: int
    cid_type: str | None = Field(default=None, alias="cidType")
    sender_id: int = Field(default=None, alias="senderId")
    type: str | None = Field(default=None)
    data: DataContent | None = Field(default=None)
    data_type: str | None = Field(default=None, alias="dataType")
    callback_data: str | None = Field(default=None, alias="callbackData")

    @field_validator("data", mode="before")
    @classmethod
    def parse_data(cls, value: Any) -> dict | Any:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed
            except json.JSONDecodeError:
                return {"text": value, "type": "text"}

        return value
