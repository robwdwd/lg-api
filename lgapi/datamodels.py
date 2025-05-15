# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
from typing import Annotated

from annotated_types import Len
from pydantic import AfterValidator, BaseModel, Field, IPvAnyAddress, IPvAnyNetwork

from lgapi.config import settings
from lgapi.validation import validate_location


class MultiPingBody(BaseModel):
    """Request body for Multi-Ping requests"""

    locations: Annotated[
        list[
            Annotated[
                str, Field(description="Source location", examples=["LON", "FRA"]), AfterValidator(validate_location)
            ]
        ],
        Len(min_length=1, max_length=settings.ping_multi_max_source),
    ]

    destinations: Annotated[
        list[
            Annotated[
                IPvAnyAddress,
                Field(description="Destination IP addresses", examples=["10.2.3.1", "8.8.8.8"]),
            ]
        ],
        Len(min_length=1, max_length=settings.bgp_multi_max_ip),
    ]


class MultiBgpBody(BaseModel):
    """Request body for Multi-Bgp requests"""

    locations: Annotated[
        list[
            Annotated[
                str, Field(description="Source location", examples=["LON", "FRA"]), AfterValidator(validate_location)
            ]
        ],
        Len(min_length=1, max_length=settings.bgp_multi_max_source),
    ]

    destinations: Annotated[
        list[
            Annotated[
                IPvAnyAddress | IPvAnyNetwork,
                Field(description="Destination IP addresses or CIDRs", examples=["10.4.8.1", "8.8.8.0/24"]),
            ]
        ],
        Len(min_length=1, max_length=settings.bgp_multi_max_ip),
    ]


# BGP Output
#
class BgpCommunity(BaseModel):
    """Community string and human readable mapping for this BGP Path"""

    community: str
    description: str | None


class BgpPath(BaseModel):
    """Individual BGP Path for the given prefix"""

    communities: list[BgpCommunity] | None = None
    metric: str | None = None
    local_pref: str | None = None
    best_path: bool | None = None
    next_hop: str | None = None
    as_path: str | list | None = None


class BgpData(BaseModel):
    """BGP Prefix"""

    prefix: Annotated[str, Field(description="Prefix in CIDR format", examples=["10.0.0.0/21", "10.1.2.0/24"])]
    paths: list[BgpPath]
    as_paths: Annotated[list[list[int]], Field(description="List of unique AS paths for this prefix.")] | None = None


class BgpResult(BaseModel):
    """BGP results"""

    parsed_output: list[BgpData] | None
    raw_output: str
    command: str | None = None
    location: str | None = None
    location_name: str | None = None
    raw_only: bool


class BgpLocation(BaseModel):
    """BGP results per location"""

    name: str
    results: BgpResult | None


class MultiBgpResult(BaseModel):
    """Multi Ping results"""

    errors: list[str]
    locations: list[BgpLocation]
    raw_only: bool


# Ping output
#
class PingData(BaseModel):
    """Ping response to destination IP Address"""

    prefix: Annotated[str, Field(description="IP Address", examples=["10.1.1.1"])]
    packet_loss: int | None = None
    rtt_min: str | None = None
    rtt_avg: str | None = None
    rtt_max: str | None = None
    packet_count: str | None = None
    packet_size: str | None = None


class PingResult(BaseModel):
    """Ping results"""

    parsed_output: list[PingData] | None
    raw_output: str
    command: str | None = None
    location: str | None = None
    location_name: str | None = None
    raw_only: bool


class PingLocation(BaseModel):
    """Ping results per location"""

    name: str
    results: PingResult | None


class MultiPingResult(BaseModel):
    """Multi Ping results"""

    errors: list[str]
    locations: list[PingLocation]
    raw_only: bool


# Traceroute output
#
class TracerouteHop(BaseModel):
    """Individual Traceroute hop"""

    hop_number: str | None = None
    ip_address: str | None = None
    rtt: str | None = None
    fqdn: str | None = None


class TracerouteData(BaseModel):
    """Traceroute hops"""

    prefix: Annotated[str, Field(description="IP Address", examples=["10.1.1.1"])]
    hops: list[TracerouteHop]


class TracerouteResult(BaseModel):
    """Traceroute results"""

    parsed_output: list[TracerouteData] | None
    raw_output: str
    command: str
    raw_only: bool


# Location output
#
class LocationResponse(BaseModel):
    """Location details"""

    code: str
    name: str
    region: str


class LocationRegionResponse(BaseModel):
    """Locations grouped by regions"""

    name: Annotated[str, Field(description="Region name", examples=["Western Europe", "Asia"])]
    locations: list[LocationResponse]
