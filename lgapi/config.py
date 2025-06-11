# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Convert .env settings into fastapi config."""


from functools import lru_cache
from typing import Literal

from aiocache import caches
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from lgapi.types.config import (
    AuthenticationConfig,
    CacheConfig,
    CommandsConfig,
    LimitsConfig,
    LocationConfig,
)


class Settings(BaseSettings):
    """Settings base class used to convert config.yml file into python"""

    title: str = Field(default="Looking Glass API")
    resolve_traceroute_hops: Literal["off", "all", "missing"] = Field(default="off")
    log_level: Literal["critical", "error", "warning", "info", "debug", "trace"] = Field(default="info")
    root_path: str = Field(default="/")
    environment: Literal["prod", "devel"] = Field(default="prod")

    server_id: str = Field(default="api1")

    cache: CacheConfig

    limits: LimitsConfig

    authentication: AuthenticationConfig

    locations: dict[str, LocationConfig]
    commands: CommandsConfig

    model_config = SettingsConfigDict(yaml_file="config.yml")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            file_secret_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()


def configure_cache() -> None:
    """Configure aiocache Redis cache if enabled."""
    cache_cfg = settings.cache

    if not cache_cfg.enabled:
        return

    redis_cfg = cache_cfg.redis
    dsn = redis_cfg.dsn
    db = int(dsn.path.lstrip("/")) if dsn.path and dsn.path != "/" else 0

    default_cache_config = {
        "cache": "aiocache.RedisCache",
        "endpoint": dsn.host,
        "port": dsn.port,
        "db": db,
        "namespace": redis_cfg.namespace,
        "timeout": redis_cfg.timeout,
        "serializer": {"class": "aiocache.serializers.PickleSerializer"},
    }

    # Only add password if it exists
    if dsn.password:
        default_cache_config["password"] = dsn.password

    caches.set_config({"default": default_cache_config})


# Set up the redis cache here otherwise it won't work with the decorators
configure_cache()
