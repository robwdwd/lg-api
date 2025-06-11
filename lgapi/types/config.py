# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Models used for Configuration validation"""
from pydantic import BaseModel, Field, RedisDsn, model_validator


class AuthCredentialsConfig(BaseModel):
    """Configuration for authentication credentials.

    Attributes:
        username (str): Username for authentication.
        password (str): Password for authentication.
    """

    username: str = Field(default="netuser")
    password: str = Field(default="password123")


class AuthenticationConfig(BaseModel):
    """Configuration for authentication groups.

    Attributes:
        groups (dict[str, AuthCredentialsConfig]): Mapping of group names to their credentials.
    """

    groups: dict[str, AuthCredentialsConfig]

    @model_validator(mode="before")
    @classmethod
    def ensure_fallback_in_groups(cls, data: dict):
        """Make sure the fallback authentication group exists."""
        if "groups" not in data or "fallback" not in data["groups"]:
            raise ValueError("The 'fallback' group must exist under 'authentication.groups'.")
        return data


class SourcesConfig(BaseModel):
    """Sources based on destination IP version"""

    ipv4: str
    ipv6: str


class LocationConfig(BaseModel):
    """Configuration for a network location.

    Attributes:
        name (str): Name of the location.
        region (str): Region name.
        country (str): Country name.
        country_iso (str): ISO country code
        device (str): Device hostname.
        type (str): Device type (i.e. juniper_junos).
        authentication (str | None): Optional authentication group name.
        source (str): Source IP or interface for ping and traceroute commands.
    """

    name: str
    region: str
    country: str
    country_iso: str
    device: str
    type: str
    authentication: str | None = None
    source: SourcesConfig


class CommandVariantsConfig(BaseModel):
    """Configuration for command variants (IPv4 and IPv6).

    Attributes:
        ipv4 (str): Command for IPv4.
        ipv6 (str): Command for IPv6.
    """

    ipv4: str
    ipv6: str


class CommandsConfig(BaseModel):
    """Configuration for supported commands and their variants.

    Attributes:
        ping (dict[str, CommandVariantsConfig]): Ping command variants.
        bgp (dict[str, CommandVariantsConfig]): BGP command variants.
        traceroute (dict[str, CommandVariantsConfig]): Traceroute command variants.
    """

    ping: dict[str, CommandVariantsConfig]
    bgp: dict[str, CommandVariantsConfig]
    traceroute: dict[str, CommandVariantsConfig]


class RedisConfig(BaseModel):
    """Configuration for Redis connection.

    Attributes:
        namespace (str): Redis namespace prefix.
        timeout (int): Connection timeout in seconds.
        dsn (RedisDsn): Redis DSN string.
    """

    namespace: str = Field(default="lgapi")
    timeout: int = Field(default=5)
    dsn: RedisDsn = Field(default="redis://localhost:6379/")


class CommandCacheConfig(BaseModel):
    """Configuration for command-level caching.

    Attributes:
        enabled (bool): Whether command caching is enabled.
        ttl (int): Time-to-live for cached commands in seconds.
    """

    enabled: bool = Field(default=False)
    ttl: int = 180


class CacheConfig(BaseModel):
    """Configuration for caching.

    Attributes:
        enabled (bool): Whether caching is enabled.
        commands (CommandCacheConfig): Command cache configuration.
        redis (RedisConfig): Redis configuration.
    """

    enabled: bool = Field(default=False)
    commands: CommandCacheConfig
    redis: RedisConfig


class MaxSourcesConfig(BaseModel):
    """Configuration for maximum allowed sources per command.

    Attributes:
        bgp (int): Max sources for BGP.
        ping (int): Max sources for ping.
    """

    bgp: int = Field(default=3)
    ping: int = Field(default=3)


class MaxDestinationsConfig(BaseModel):
    """Configuration for maximum allowed destinations per command.

    Attributes:
        bgp (int): Max destinations for BGP.
        ping (int): Max destinations for ping.
    """

    bgp: int = Field(default=5)
    ping: int = Field(default=5)


class LimitsConfig(BaseModel):
    """Configuration for command limits.

    Attributes:
        max_sources (MaxSourcesConfig): Maximum sources configuration.
        max_destinations (MaxDestinationsConfig): Maximum destinations configuration.
    """

    max_sources: MaxSourcesConfig
    max_destinations: MaxDestinationsConfig
