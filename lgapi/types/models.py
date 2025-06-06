# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Models used for API output"""
from typing import Annotated, Union

from annotated_types import Len
from pydantic import AfterValidator, BaseModel, Field, IPvAnyAddress, IPvAnyNetwork

from lgapi.config import settings
from lgapi.validation import validate_location

LocationStr = Annotated[
    str, Field(description="Source location", examples=["LON", "FRA", "SIN"]), AfterValidator(validate_location)
]

DestIP = Annotated[
    IPvAnyAddress, Field(description="Destination IP address", examples=["10.2.3.1", "8.8.8.8", "1.1.1.1"])
]

DestIPNet = Annotated[
    Union[IPvAnyAddress, IPvAnyNetwork],
    Field(description="Destination IP or Prefix", examples=["10.4.8.1", "8.8.8.0/24", "4.0.0.0/9"]),
]

IPAddressStr = Annotated[str, Field(description="IP Address", examples=["10.1.1.1", "4.4.4.4", "9.9.9.9"])]
PrefixStr = Annotated[str, Field(description="Prefix in CIDR format", examples=["10.0.0.0/21", "10.1.2.0/24"])]


class MultiPingBody(BaseModel):
    """Request body for Multi-Ping requests"""

    locations: Annotated[
        list[LocationStr],
        Len(min_length=1, max_length=settings.limits.max_sources.ping),
    ]

    destinations: Annotated[
        list[DestIP],
        Len(min_length=1, max_length=settings.limits.max_destinations.ping),
    ]


class MultiBgpBody(BaseModel):
    """Request body for Multi-Bgp requests"""

    locations: Annotated[
        list[LocationStr],
        Len(min_length=1, max_length=settings.limits.max_sources.bgp),
    ]

    destinations: Annotated[
        list[DestIPNet],
        Len(min_length=1, max_length=settings.limits.max_destinations.bgp),
    ]


# Base models
#
class BaseResult(BaseModel):
    """Base results"""

    parsed_output: list[object] | None
    raw_output: str
    command: str | None = None
    location: str | None = None
    location_name: str | None = None
    raw_only: bool = False


class BaseLocation(BaseModel):
    """Results per location"""

    name: str
    results: BaseResult | None


class BaseMultiResult(BaseModel):
    """Multi result Base"""

    errors: list[str]
    locations: list[BaseLocation]
    raw_only: bool


# BGP Output
#
class ASNOrganization(BaseModel):
    """Organisation for the ASN"""

    orgName: str


class ASNCountry(BaseModel):
    """Origin country for the ASN"""

    iso: str
    name: str


class ASNInfoEntry(BaseModel):
    """ASN Information from Caida AS Rank"""

    asnName: str
    rank: int
    organization: ASNOrganization
    country: ASNCountry


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

    prefix: PrefixStr
    paths: list[BgpPath]
    as_paths: Annotated[list[list[int]], Field(description="List of unique AS paths for this prefix.")] | None = None
    asn_info: dict[str, ASNInfoEntry] | dict = Field(default_factory=dict)


class BgpResult(BaseResult):
    """BGP results"""

    parsed_output: list[BgpData] | None


class BgpLocation(BaseLocation):
    """BGP results per location"""

    results: BgpResult | None


class MultiBgpResult(BaseMultiResult):
    """Multi Ping results"""

    locations: list[BgpLocation]


# Ping output
#
class PingData(BaseModel):
    """Ping response to destination IP Address"""

    ip_address: IPAddressStr
    packet_loss: int | None = None
    rtt_min: str | None = None
    rtt_avg: str | None = None
    rtt_max: str | None = None
    packet_count: str | None = None
    packet_size: str | None = None


class PingResult(BaseResult):
    """Ping results"""

    parsed_output: list[PingData] | None


class PingLocation(BaseLocation):
    """Ping results per location"""

    results: PingResult | None


class MultiPingResult(BaseMultiResult):
    """Multi Ping results"""

    locations: list[PingLocation]


# Traceroute output
#
class IPAddressInfo(BaseModel):
    """Additional IP address information"""

    asn: int | None = None
    bgp_prefix: PrefixStr | None = None
    registry: str | None = None
    asrank: ASNInfoEntry | None = None


class TracerouteHop(BaseModel):
    """Individual Traceroute hop"""

    hop_number: str | None = None
    ip_address: str | None = None
    rtt: str | None = None
    fqdn: str | None = None
    info: IPAddressInfo | None = None


class TracerouteData(BaseModel):
    """Traceroute hops"""

    ip_address: IPAddressStr
    hops: list[TracerouteHop]


class TracerouteResult(BaseResult):
    """Traceroute results"""

    parsed_output: list[TracerouteData] | None


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
