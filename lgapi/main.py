# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
#import pprint
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, TypedDict, cast

from aiocache import caches
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, Limits
from pydantic import AfterValidator, IPvAnyAddress

from lgapi import logger
from lgapi.commands import execute_multiple_commands, execute_single_command
from lgapi.config import settings
from lgapi.database import init_community_map_db
from lgapi.locations import get_locations, get_locations_by_region
from lgapi.processing import (
    process_bgp_output,
    process_ping_output,
    process_traceroute_output,
)
from lgapi.ttp import get_template, parse_txt
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

#pp = pprint.PrettyPrinter(indent=2, width=120)

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
    result = await execute_single_command(location, "ping", str(destination))

    # Parse output if raw_only is False and a template exists
    parsed_output = []
    if not raw and (template_name := get_template("ping", LOCATIONS_CFG[location].type)):
        parsed_result = parse_txt(result, template_name)
        if isinstance(parsed_result, list) and parsed_result:
            parsed_output = await process_ping_output(parsed_result[0])

    if not parsed_output:
        raw = True

    return {
        "parsed_output": parsed_output,
        "raw_output": result,
        "raw_only": raw,
        "command": "bgp",
        "location": location,
        "location_name": LOCATIONS_CFG[location].name,
    }


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
    result = await execute_single_command(location, "traceroute", str(destination))

    # Parse output if raw_only is False and a template exists
    parsed_output = []
    if not raw and (template_name := get_template("traceroute", LOCATIONS_CFG[location].type)):
        parsed_result = parse_txt(result, template_name)
        if isinstance(parsed_result, list) and parsed_result and parsed_result[0]:
            httpclient = cast(AsyncClient, request.state.httpclient)
            parsed_output = await process_traceroute_output(parsed_result[0], LOCATIONS_CFG[location].type, httpclient)

    if not parsed_output:
        raw = True

    return {
        "parsed_output": parsed_output,
        "raw_output": result,
        "raw_only": raw,
        "command": "bgp",
        "location": location,
        "location_name": LOCATIONS_CFG[location].name,
    }


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
    result = await execute_single_command(location, "bgp", str(destination))

    # Parse output if raw_only is False and a template exists
    parsed_output = []
    if not raw and (template_name := get_template("bgp", LOCATIONS_CFG[location].type)):
        parsed_result = parse_txt(result, template_name)
        if isinstance(parsed_result, list) and parsed_result:
            httpclient = cast(AsyncClient, request.state.httpclient)
            parsed_output = await process_bgp_output(parsed_result[0], httpclient)

    if not parsed_output:
        raw = True

    return {
        "parsed_output": parsed_output,
        "raw_output": result,
        "raw_only": raw,
        "command": "bgp",
        "location": location,
        "location_name": LOCATIONS_CFG[location].name,
    }


@app.post("/multi/ping", response_model=MultiPingResult)
async def multi_ping(targets: MultiPingBody, raw: bool = False) -> dict:
    """Ping from multiple sources to multiple destinations"""

    output_table = {"locations": [], "errors": [], "raw_only": raw}

    results = await execute_multiple_commands(targets, "ping")

    for result in results:

        if "error" in result:
            output_table["errors"].append(f"{result['location']}: {result['error']}")
        else:
            location = result["location"]
            location_name = LOCATIONS_CFG[location].name

            new_result = {
                "parsed_output": [],
                "raw_output": result["result"],
                "raw_only": raw,
                "command": "ping",
                "location": location,
                "location_name": location_name,
            }

            if not raw and (template_name := get_template("ping", LOCATIONS_CFG[location].type)):
                parsed_result = parse_txt(result["result"], template_name)
                if isinstance(parsed_result, list) and parsed_result:
                    new_result["parsed_output"] = await process_ping_output(parsed_result[0])

                new_result["raw_only"] = not new_result["parsed_output"]

            output_table["locations"].append({"name": location_name, "results": new_result})

    return output_table


@app.post("/multi/bgp", response_model=MultiBgpResult)
async def multi_bgp(request: Request, targets: MultiBgpBody, raw: bool = False) -> dict:
    """Get BGP output from multiple sources to multiple destinations"""
    output_table = {"locations": [], "errors": [], "raw_only": raw}

    results = await execute_multiple_commands(targets, "bgp")

    for result in results:

        if "error" in result:
            output_table["errors"].append(f"{result['location']}: {result['error']}")
        else:
            location = result["location"]
            location_name = LOCATIONS_CFG[location].name

            new_result = {
                "parsed_output": [],
                "raw_output": result["result"],
                "raw_only": raw,
                "command": "bgp",
                "location": location,
                "location_name": location_name,
            }

            if not raw and (template_name := get_template("bgp", LOCATIONS_CFG[location].type)):
                parsed_result = parse_txt(result["result"], template_name)
                if isinstance(parsed_result, list) and parsed_result:
                    httpclient = cast(AsyncClient, request.state.httpclient)
                    new_result["parsed_output"] = await process_bgp_output(parsed_result[0], httpclient)

                new_result["raw_only"] = not new_result["parsed_output"]

            output_table["locations"].append({"name": location_name, "results": new_result})

    return output_table
