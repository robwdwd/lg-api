# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Device command runner."""
import asyncio
from typing import Any

from fastapi import HTTPException
from scrapli import AsyncScrapli
from scrapli.exceptions import ScrapliException
from scrapli.response import MultiResponse, Response

from lgapi.commands import DEFAULT_TIMEOUT, get_command_timeout, get_multi_commands
from lgapi.config import settings
from lgapi.datamodels import MultiBgpBody, MultiPingBody
from lgapi.processing import (
    process_bgp_output,
    process_ping_output,
    process_traceroute_output,
)
from lgapi.ttp import get_template, parse_txt

LOCATIONS_CFG = settings.lg_config["locations"]


def get_default_args(hostname: str, device_type: str) -> dict:
    """Set up some default device arguments."""

    return {
        "platform": device_type,
        "host": hostname,
        "auth_strict_key": False,
        "transport": "asyncssh",
        "auth_username": settings.username,
        "auth_password": settings.password,
    }


async def execute_on_device(
    hostname: str,
    device_type: str,
    cli_cmds: list[str] | str,
    timeout: int = DEFAULT_TIMEOUT,
) -> MultiResponse | Response:
    """Execute the command(s) on the network device."""
    device = get_default_args(hostname, device_type)

    async with AsyncScrapli(**device) as net_connect:
        if isinstance(cli_cmds, str):
            return await net_connect.send_command(command=cli_cmds, timeout_ops=timeout)

        return await net_connect.send_commands(commands=cli_cmds, timeout_ops=timeout)


async def execute_on_devices(hostname: str, device: dict, command: str) -> tuple[str, str]:
    """Run multiple commands on the device and parse/process the output"""
    try:
        response = await execute_on_device(
            hostname=hostname,
            device_type=device["type"],
            cli_cmds=device["cmds"],
            timeout=get_command_timeout(command),
        )

    except (ScrapliException, OSError) as err:
        raise Exception(f"Error getting output for {device['location']}") from err

    raw_output = "\n".join(resp.result for resp in response.data)

    return (hostname, raw_output)


async def process_response(result: str, template: str, command: str, device_type: str) -> list:
    """Process the device output based on command type."""

    parsed_result = parse_txt(result, template)

    if isinstance(parsed_result, list) and parsed_result:
        if command == "bgp":
            return await process_bgp_output(parsed_result[0])
        if command == "ping":
            return await process_ping_output(parsed_result[0])
        if command == "traceroute":
            return await process_traceroute_output(parsed_result[0], device_type)

    return []


def organise_by_location(results: list, raw_only: bool = False) -> dict:
    """Organise results by location."""

    output_table = {"locations": [], "errors": [], "raw_only": raw_only}

    for result in results:
        if isinstance(result, Exception):
            output_table["errors"].append(str(result))
        else:
            location = result["location"]
            output_table["locations"].append({"name": LOCATIONS_CFG[location]["name"], "results": result})

    return output_table


async def gather_device_results(devices: dict[str, Any], command: str) -> list:
    """Gather responses from devices asynchronously when running a multi command."""
    tasks = [execute_on_devices(hostname, device, command) for hostname, device in devices.items()]
    return await asyncio.gather(*tasks, return_exceptions=True)


async def do_multi_lg_command(targets: MultiPingBody | MultiBgpBody, command: str, raw_only: bool = False) -> dict:
    """Run looking glass commands on multiple devices and destination"""
    locations = list(dict.fromkeys(targets.locations))

    # Convert IP list to strings and remove any duplicates
    ipaddresses = list(dict.fromkeys(map(str, targets.destinations)))

    devices = get_multi_commands(locations, ipaddresses, command)

    # Assign templates and check if any are missing
    for device in devices.values():
        template_name = get_template(command, device["type"])
        device["template"] = template_name

        if not template_name:
            raw_only = True

    try:
        results = await gather_device_results(devices, command, raw_only)
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing multiple {command} commands: {err}",
        ) from err

    return organise_by_location(results, raw_only)
