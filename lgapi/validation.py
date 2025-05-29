# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import Any

from pydantic import GetJsonSchemaHandler
from pydantic.annotated_handlers import GetCoreSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, PydanticCustomError, core_schema

from lgapi.config import settings
from lgapi.types import IPvAnyNetworkOrIPType

LOCATIONS_CFG = settings.lg_config["locations"]


class IPNetOrAddress:
    """Validate an IPv4 or IPv6 network or IP address."""

    __slots__ = ()

    def __new__(cls, value: str) -> IPvAnyNetworkOrIPType:
        """Validate an IPv4 or IPv6 network or address."""
        for constructor, kwargs in [
            (IPv4Address, {"address": value}),
            (IPv6Address, {"address": value}),
            (IPv4Network, {"address": value, "strict": False}),
            (IPv6Network, {"address": value, "strict": False}),
        ]:
            try:
                return constructor(**kwargs)
            except ValueError:
                continue
        raise PydanticCustomError("ip_or_network", "Value is not a valid IPv4 or IPv6 network or address")

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        field_schema = {}
        field_schema.update(type="string", format="ipaddressornetwork", examples=["10.1.1.1", "10.2.1.0/24"])
        return field_schema

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source: type[Any],
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(
            cls._validate, serialization=core_schema.to_string_ser_schema()
        )

    @classmethod
    def _validate(cls, input_value: str, /) -> IPvAnyNetworkOrIPType:
        return cls(input_value)  # type: ignore[return-value]


def validate_location(location: str):
    """Validate a location Key"""

    if location not in LOCATIONS_CFG:
        raise ValueError("Location not found")
    return location
