# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Filter Gen and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Convert .env settings into fastapi config."""


import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from yaml import CSafeLoader as Loader
except ImportError:
    from yaml import Loader


def load_config(config_file: str):
    """Loads the looking glass configuration.

    Args:
        config_file (str): filename to loads

    Returns:
        dict: Configuration dictionary
    """
    with open(config_file, "r") as conf:
        cfg = yaml.load(conf, Loader)
        return cfg


def get_locations(locations: dict) -> list:
    """Get a list of locations from config file.

    Returns:
        dict: Locations
    """
    new_locations = []

    for location, data in locations.items():
        new_locations.append(
            {
                "code": location,
                "name": data["name"],
                "region": data["region"],
            }
        )

    return new_locations


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

    lg_config: dict = load_config(config_file)
    device_locations: list = get_locations(lg_config["locations"])


settings = Settings()
