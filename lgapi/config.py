# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Filter Gen and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Convert .env settings into fastapi config."""


from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from yaml import CSafeLoader as Loader
except ImportError:
    from yaml import Loader


def load_config(config_file: str) -> dict[str, Any]:
    """Loads the looking glass api configuration"""
    with open(config_file, "r") as conf:
        return yaml.load(conf, Loader)
        


def get_locations(locations: dict) -> list:
    """Get a list of locations from config file."""
    return [
        {
            "code": location,
            "name": data["name"],
            "region": data["region"],
        }
        for location, data in locations.items()
    ]


class Settings(BaseSettings):
    """Settings base class used to convert .env file into python"""

    username: str
    password: str
    config_file: str = "config.yml"
    ping_multi_max_source: int = 3
    ping_multi_max_ip: int = 5
    bgp_multi_max_source: int = 3
    bgp_multi_max_ip: int = 10
    log_level: str
    root_path: str = "/"
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    lg_config: dict[str, Any] = load_config(config_file)
    device_locations: list[dict[str, str]]  = get_locations(lg_config["locations"])


settings = Settings()
