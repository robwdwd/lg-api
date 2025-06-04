# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
from pydantic import BaseModel, Field, RedisDsn, model_validator


class AuthCredentials(BaseModel):
    username: str = Field(default="netuser")
    password: str = Field(default="password123")


class AuthenticationConfig(BaseModel):
    groups: dict[str, AuthCredentials]

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


class CommandVariants(BaseModel):
    ipv4: str
    ipv6: str


class CommandsConfig(BaseModel):
    ping: dict[str, CommandVariants]
    bgp: dict[str, CommandVariants]
    traceroute: dict[str, CommandVariants]


class RedisConfig(BaseModel):
    enabled: bool = Field(default=False)
    namespace: str = Field(default="lgapi")
    timeout: int = Field(default=5)
    dsn: RedisDsn = Field(default="redis://localhost:6379/")


class CacheConfig(BaseModel):
    redis: RedisConfig


class MaxSources(BaseModel):
    bgp: int = Field(default=3)
    ping: int = Field(default=3)


class MaxDestinations(BaseModel):
    bgp: int = Field(default=3)
    ping: int = Field(default=3)


class LimitsConfig(BaseModel):
    max_sources: MaxSources
    max_destinations: MaxDestinations
