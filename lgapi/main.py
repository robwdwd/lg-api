# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
# import pprint
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, TypedDict, cast

from aiocache import caches
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, Limits
from pydantic import AfterValidator, IPvAnyAddress
from scrapli.exceptions import ScrapliException

from lgapi import logger
from lgapi.commands import execute_multiple_commands, execute_single_command
from lgapi.config import settings
from lgapi.database import init_community_map_db
from lgapi.locations import get_locations, get_locations_by_region
from lgapi.parsing import parse_command_output, parse_multi_command_results
from lgapi.types.models import (
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
from lgapi.validation import IPNetOrAddress, validate_location

# pp = pprint.PrettyPrinter(indent=2, width=120)

LOCATIONS_CFG = settings.locations

if settings.environment == "devel":
    logger.setLevel(str(settings.log_level).upper())


class State(TypedDict):
    """Stores the state variables from the lifespan"""

    httpclient: AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    """Lifespan for setup etc with fastAPI"""

    # Populate the community mapping database
    logger.debug("Building BGP community database")
    await init_community_map_db()

    # Set up the http client
    logger.debug("Starting HTTPX Async client")
    httpclient = AsyncClient(limits=Limits(max_connections=None, max_keepalive_connections=20))

    logger.debug("Clearing cache")
    cache = caches.get("default")
    await cache.clear()

    yield {"httpclient": httpclient}
    await httpclient.aclose()
    logger.debug("Stopped HTTPX Async client")


app = FastAPI(
    title=settings.title,
    lifespan=lifespan,
    debug=(settings.environment == "devel"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/locations", response_model=list[LocationResponse])
async def locations() -> list:
    """Get list of available locations."""
    return get_locations(settings.locations)


@app.get("/locations/regional", response_model=list[LocationRegionResponse])
async def locations_region() -> list:
    """Get list of available locations, grouped by region."""
    return await get_locations_by_region(settings.locations)


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
    loc_config = LOCATIONS_CFG[location]
    try:
        result = await execute_single_command(location, "ping", str(destination))
    except (ScrapliException, OSError) as err:
        logger.warning(
            "Error getting device output from '%s' (%s) for command ping: %s", loc_config.device, location, err
        )

        raise HTTPException(
            status_code=500,
            detail=f"Error executing command 'ping' at location '{loc_config.name}'",
        ) from err

    return await parse_command_output(
        location=location,
        result=result,
        command="ping",
        raw=raw,
    )


@app.get("/traceroute/{location}/{destination}", response_model=TracerouteResult)
async def traceroute(
    request: Request,
    location: Annotated[str, AfterValidator(validate_location)],
    destination: IPvAnyAddress,
    raw: bool = False,
) -> dict:
    """Traceroute to a destination from a location.

    - **location**: Source location code to traceroute from
    - **destination**: Destination IP address to traceroute to
    - **raw**: Return only raw output without any parsing.
    """
    loc_config = LOCATIONS_CFG[location]
    try:
        result = await execute_single_command(location, "traceroute", str(destination))
    except (ScrapliException, OSError) as err:
        logger.warning(
            "Error getting device output from '%s' (%s) for command traceroute: %s", loc_config.device, location, err
        )

        raise HTTPException(
            status_code=500,
            detail=f"Error executing command 'traceroute' at location '{loc_config.name}'",
        ) from err

    httpclient = cast(AsyncClient, request.state.httpclient) if not raw else None
    return await parse_command_output(
        location=location,
        result=result,
        command="traceroute",
        raw=raw,
        httpclient=httpclient,
    )


@app.get("/bgp/{location}/{destination:path}", response_model=BgpResult)
async def bgp(
    request: Request,
    location: Annotated[str, AfterValidator(validate_location)],
    destination: IPNetOrAddress,
    raw: bool = False,
) -> dict:
    """Check BGP route/path from a location.

    - **location**: Source location code to check from
    - **destination**: Destination IP address or CIDR to view
    - **raw**: Return only raw output without any parsing.
    """
    loc_config = LOCATIONS_CFG[location]
    try:
        result = await execute_single_command(location, "bgp", str(destination))
    except (ScrapliException, OSError) as err:
        logger.warning(
            "Error getting device output from '%s' (%s) for command bgp: %s", loc_config.device, location, err
        )

        raise HTTPException(
            status_code=500,
            detail=f"Error executing command 'bgp' at location '{loc_config.name}'",
        ) from err

    httpclient = cast(AsyncClient, request.state.httpclient) if not raw else None
    return await parse_command_output(
        location=location,
        result=result,
        command="bgp",
        raw=raw,
        httpclient=httpclient,
    )


@app.post("/multi/ping", response_model=MultiPingResult)
async def multi_ping(targets: MultiPingBody, raw: bool = False) -> dict:
    """Ping from multiple sources to multiple destinations"""

    results = await execute_multiple_commands(targets, "ping")
    return await parse_multi_command_results(
        results=results,
        command="ping",
        raw=raw,
    )


@app.post("/multi/bgp", response_model=MultiBgpResult)
async def multi_bgp(request: Request, targets: MultiBgpBody, raw: bool = False) -> dict:
    """Get BGP output from multiple sources to multiple destinations"""

    results = await execute_multiple_commands(targets, "bgp")
    httpclient = cast(AsyncClient, request.state.httpclient) if not raw else None
    return await parse_multi_command_results(
        results=results,
        command="bgp",
        raw=raw,
        httpclient=httpclient,
    )
