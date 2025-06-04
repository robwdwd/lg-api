# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
from pydantic import BaseModel, Field, RedisDsn, model_validator


class AuthCredentialsConfig(BaseModel):
    username: str = Field(default="netuser")
    password: str = Field(default="password123")


class AuthenticationConfig(BaseModel):
    groups: dict[str, AuthCredentialsConfig]

    @model_validator(mode="before")
    @classmethod
    def ensure_fallback_in_groups(cls, data: dict):
        """Make sure the fallback authentication group exists"""
        if "groups" not in data or "fallback" not in data["groups"]:
            raise ValueError("The 'fallback' group must exist under 'authentication.groups'.")
        return data


class LocationConfig(BaseModel):
    name: str
    region: str
    device: str
    type: str
    authentication: str | None = None
    source: str


class CommandVariantsConfig(BaseModel):
    ipv4: str
    ipv6: str


class CommandsConfig(BaseModel):
    ping: dict[str, CommandVariantsConfig]
    bgp: dict[str, CommandVariantsConfig]
    traceroute: dict[str, CommandVariantsConfig]


class RedisConfig(BaseModel):
    namespace: str = Field(default="lgapi")
    timeout: int = Field(default=5)
    dsn: RedisDsn = Field(default="redis://localhost:6379/")


class CommandCacheConfig(BaseModel):
    enabled: bool = Field(default=False)
    ttl: int = 60


class CacheConfig(BaseModel):
    enabled: bool = Field(default=False)
    commands: CommandCacheConfig
    redis: RedisConfig


class MaxSourcesConfig(BaseModel):
    bgp: int = Field(default=3)
    ping: int = Field(default=3)


class MaxDestinationsConfig(BaseModel):
    bgp: int = Field(default=3)
    ping: int = Field(default=3)


class LimitsConfig(BaseModel):
    max_sources: MaxSourcesConfig
    max_destinations: MaxDestinationsConfig
