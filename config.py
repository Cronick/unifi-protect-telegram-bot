from typing import Any

import tomli
from loguru import logger
from pydantic import BaseModel, ValidationError

class Unifi(BaseModel):
    hostname: str
    username: str
    password: str
    check_interval: int

class Network(BaseModel):
    devices: list

class Telegram(BaseModel):
    bot_token: str
    chat_id: str
    startup_msg: bool

class Config(BaseModel):
    unifi: Unifi
    network: Network
    telegram: Telegram


try:
    with open("config.toml", mode="rb") as _config_file:
        _raw_config = tomli.load(_config_file)

    try:
        _config = Config(**_raw_config)
    except ValidationError as e:
        logger.error(f"Config validation error!\n{e}")

        for error in e.errors():
            type_: str = error.get("type", "")
            loc: tuple[str] = error.get("loc", ("",))
            data: dict[str, Any] = error.get("input", {})
        exit()
except FileNotFoundError:
    logger.critical("No config.toml found!")
    exit()

config = _config