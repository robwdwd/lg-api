# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
import pprint
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, TypedDict, cast

from aiocache import caches
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, Limits
from pydantic import AfterValidator, IPvAnyAddress

from lgapi.commands import execute_multiple_commands, execute_single_command
from lgapi.config import settings
from lgapi.database import init_community_map_db
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
from lgapi.processing import (
    process_bgp_output,
    process_location_output_by_region,
    process_ping_output,
    process_traceroute_output,
)
from lgapi.ttp import get_template, parse_txt
from lgapi.validation import IPNetOrAddress, validate_location

pp = pprint.PrettyPrinter(indent=2, width=120)

LOCATIONS_CFG = settings.lg_config["locations"]


class State(TypedDict):
    """Stores the state variables from the lifespan"""

    httpclient: AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    """Lifespan for setup etc with fastAPI"""

    # Populate the community mapping database
    init_community_map_db()

    # Set up the http client
    httpclient = AsyncClient(limits=Limits(max_connections=None, max_keepalive_connections=20))

    # Configure aiocache to use Redis
    if settings.use_redis_cache:
        caches.set_config(
            {
                "default": {
                    "cache": "aiocache.RedisCache",
                    "endpoint": "localhost",
                    "port": 6379,
                    "serializer": {"class": "aiocache.serializers.PickleSerializer"},
                }
            }
        )

    yield {"httpclient": httpclient}
    await httpclient.aclose()


app = FastAPI(debug=settings.debug, lifespan=lifespan)

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
    result = await execute_single_command(location, "ping", str(destination))

    # Parse output if raw_only is False and a template exists
    parsed_output = []
    if not raw and (template_name := get_template("ping", LOCATIONS_CFG[location]["type"])):
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
        "location_name": LOCATIONS_CFG[location]["name"],
    }


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
    result = await execute_single_command(location, "traceroute", str(destination))

    # Parse output if raw_only is False and a template exists
    parsed_output = []
    if not raw and (template_name := get_template("traceroute", LOCATIONS_CFG[location]["type"])):
        parsed_result = parse_txt(result, template_name)
        if isinstance(parsed_result, list) and parsed_result:
            parsed_output = await process_traceroute_output(parsed_result[0], LOCATIONS_CFG[location]["type"])

    if not parsed_output:
        raw = True

    return {
        "parsed_output": parsed_output,
        "raw_output": result,
        "raw_only": raw,
        "command": "bgp",
        "location": location,
        "location_name": LOCATIONS_CFG[location]["name"],
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
    if not raw and (template_name := get_template("bgp", LOCATIONS_CFG[location]["type"])):
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
        "location_name": LOCATIONS_CFG[location]["name"],
    }


@app.post("/multi/ping", response_model=MultiPingResult)
async def multi_ping(targets: MultiPingBody, raw: bool = False) -> dict:
    """Ping from multiple sources to multiple destinations"""

    output_table = {"locations": [], "errors": [], "raw_only": raw}

    results = await execute_multiple_commands(targets, "ping")

    for result in results:

        if isinstance(result, Exception):
            output_table["errors"].append(str(result))
        else:
            location = result["location"]
            location_name = LOCATIONS_CFG[location]["name"]

            new_result = {
                "parsed_output": [],
                "raw_output": result["result"],
                "raw_only": raw,
                "command": "ping",
                "location": location,
                "location_name": location_name,
            }

            if not raw and (template_name := get_template("ping", LOCATIONS_CFG[location]["type"])):
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

        if isinstance(result, Exception):
            output_table["errors"].append(str(result))
        else:
            location = result["location"]
            location_name = LOCATIONS_CFG[location]["name"]

            new_result = {
                "parsed_output": [],
                "raw_output": result["result"],
                "raw_only": raw,
                "command": "bgp",
                "location": location,
                "location_name": location_name,
            }

            if not raw and (template_name := get_template("bgp", LOCATIONS_CFG[location]["type"])):
                parsed_result = parse_txt(result["result"], template_name)
                if isinstance(parsed_result, list) and parsed_result:
                    httpclient = cast(AsyncClient, request.state.httpclient)
                    new_result["parsed_output"] = await process_bgp_output(parsed_result[0], httpclient)

                new_result["raw_only"] = not new_result["parsed_output"]

            output_table["locations"].append({"name": location_name, "results": new_result})

    return output_table
