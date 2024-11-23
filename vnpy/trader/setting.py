"""
Global setting of the trading platform.
"""

from logging import CRITICAL
from typing import Dict, Any
from tzlocal import get_localzone_name

from .utility import load_json


SETTINGS: Dict[str, Any] = {
    "font.family": "微软雅黑",
    "font.size": 12,

    "log.active": True,
    "log.level": CRITICAL,
    "log.console": True,
    "log.file": True,

    "email.server": "smtp.qq.com",
    "email.port": 465,
    "email.username": "",
    "email.password": "",
    "email.sender": "",
    "email.receiver": "",

    "longbridge.app_key": "",
    "longbridge.app_secret": "",
    "longbridge.access_token": "",

    "datafeed.key": "",
    "datafeed.app_secret": "",
    "datafeed.access_token": "",
    'datafeed.name': '',
    'datafeed.password': '',

    "database.timezone": get_localzone_name(),
    "database.name": "sqlite",
    "database.database": "vnpy",
    "database.host": "localhost",
    "database.port": 3307,
    "database.user": "root",
    "database.password": "123456"
}


# Load global setting from json file.
SETTING_FILENAME: str = "vt_setting.json"
SETTINGS.update(load_json(SETTING_FILENAME))


def get_settings(prefix: str = "") -> Dict[str, Any]:
    prefix_length: int = len(prefix)
    settings = {k[prefix_length:]: v for k, v in SETTINGS.items() if k.startswith(prefix)}
    return settings
