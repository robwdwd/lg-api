# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Convert .env settings into fastapi config."""


from typing import Any, Literal

import yaml
from aiocache import caches
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from yaml import CSafeLoader as Loader
except ImportError:
    from yaml import Loader



def load_config(config_file: str) -> dict[str, Any]:
    """Loads the looking glass api configuration"""
    with open(config_file, "r") as conf:
        return yaml.load(conf, Loader)


def get_locations(locations: dict[str, Any]) -> list[dict[str, str]]:
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
    title: str = 'Looking Glass API'
    ping_multi_max_source: int = 3
    ping_multi_max_ip: int = 5
    bgp_multi_max_source: int = 3
    bgp_multi_max_ip: int = 5
    resolve_traceroute_hops: Literal['off', 'all', 'missing'] = 'off'
    log_level: Literal['critical', 'error', 'warning', 'info', 'debug', 'trace'] = 'info'
    root_path: str = "/"
    environment: Literal['prod', 'devel'] = 'prod'

    # Redis configuration
    use_redis_cache: bool = False
    redis_namespace: str = 'lgapi'
    redis_password: str | None = None
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_timeout: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    lg_config: dict[str, Any] = {}
    device_locations: list[dict[str, str]] = []

    def model_post_init(self, __context: Any) -> None:
        self.lg_config = load_config(self.config_file)
        self.device_locations = get_locations(self.lg_config["locations"])


settings = Settings()

# Set up the redis cache here otherwise it won't work with the decorators
if settings.use_redis_cache:
    caches.set_config(
        {
            "default": {
                "cache": "aiocache.RedisCache",
                "endpoint": settings.redis_host,
                "namespace": settings.redis_namespace,
                "port": settings.redis_port,
                "password": settings.redis_password,
                "timeout": settings.redis_timeout,
                "serializer": {"class": "aiocache.serializers.PickleSerializer"},
            }
        }
    )

