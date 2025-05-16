# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AfterValidator, IPvAnyAddress

from lgapi.config import settings
from lgapi.datamodels import (
    BgpResult,
    LocationRegionResponse,
    LocationResponse,
    MultiBgpBody,
    MultiBgpResult,
    MultiPingBody,
    MultiPingResult,
    PingResult,
    TracerouteResult,
)
from lgapi.device import do_multi_lg_command, do_single_lg_command
from lgapi.maps import process_location_output_by_region
from lgapi.validation import IPNetOrAddress, validate_location

app = FastAPI(debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def execute_command(location: str, command: str, destination: str, raw: bool) -> dict:
    """Helper function to execute a command."""
    try:
        return await do_single_lg_command(location=location, command=command, ipaddress=destination, raw_only=raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")


@app.get("/locations", response_model=list[LocationResponse])
async def locations() -> list:
    """Get list of available locations."""
    return settings.device_locations


@app.get("/locations/regional", response_model=list[LocationRegionResponse])
async def locations_region() -> list:
    """Get list of available locations, grouped by region."""
    return await process_location_output_by_region(settings.device_locations)


@app.get("/ping/{location}/{destination}", response_model=PingResult)
async def ping(
    location: Annotated[str, AfterValidator(validate_location)],
    destination: IPvAnyAddress,
    raw: bool = False,
) -> dict:
    """Ping a destination from a location.

    - **location**: Source location code to ping from
    - **destination**: Destination IP address to ping
    - **raw**: Return only raw output without any parsing.
    """
    return await execute_command(location, "ping", str(destination), raw)


@app.get("/traceroute/{location}/{destination}", response_model=TracerouteResult)
async def traceroute(
    location: Annotated[str, AfterValidator(validate_location)],
    destination: IPvAnyAddress,
    raw: bool = False,
) -> dict:
    """Traceroute to a destination from a location.

    - **location**: Source location code to traceroute from
    - **destination**: Destination IP address to traceroute to
    - **raw**: Return only raw output without any parsing.
    """
    return await execute_command(location, "traceroute", str(destination), raw)


@app.get("/bgp/{location}/{destination:path}", response_model=BgpResult)
async def bgp(
    location: Annotated[str, AfterValidator(validate_location)],
    destination: IPNetOrAddress,
    raw: bool = False,
) -> dict:
    """Check BGP route/path from a location.

    - **location**: Source location code to check from
    - **destination**: Destination IP address or CIDR to view
    - **raw**: Return only raw output without any parsing.
    """
    return await execute_command(location, "bgp", str(destination), raw)


@app.post("/multi/ping", response_model=MultiPingResult)
async def multi_ping(targets: MultiPingBody, raw: bool = False) -> dict:
    """Ping from multiple sources to multiple destinations"""
    return await do_multi_lg_command(targets, "ping", raw)


@app.post("/multi/bgp", response_model=MultiBgpResult)
async def multi_bgp(targets: MultiBgpBody, raw: bool = False) -> dict:
    """Get BGP output from multiple sources to multiple destinations"""
    return await do_multi_lg_command(targets, "bgp", raw)
