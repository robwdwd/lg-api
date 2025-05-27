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

from lgapi.commands import get_cmd, get_multi_commands
from lgapi.config import settings
from lgapi.datamodels import MultiBgpBody, MultiPingBody
from lgapi.maps import (
    process_bgp_output,
    process_ping_output,
    process_traceroute_output,
)
from lgapi.ttp import get_template, parse_txt

LOCATIONS_CFG = settings.lg_config["locations"]

DEFAULT_TIMEOUT = 60
COMMAND_TIMEOUTS = {"traceroute": 600}


def get_command_timeout(command: str) -> int:
    """Get timeout for a specific command."""
    return COMMAND_TIMEOUTS.get(command, DEFAULT_TIMEOUT)


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


async def get_multi_results(hostname: str, device: dict, command: str, raw_only: bool = False) -> dict:
    """Run multiple commands on the device and parse/process the output"""
    parsed_output = []
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

    if not raw_only and (template := device.get("template")):
        parsed_output = await process_response(raw_output, template, command, device["type"])
        if not parsed_output:
            raw_only = True

    return {
        "parsed_output": parsed_output,
        "raw_output": raw_output,
        "command": command,
        "location": device["location"],
        "location_name": device["location_name"],
        "raw_only": raw_only,
    }


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


async def gather_device_results(devices: dict[str, Any], command: str, raw_only: bool) -> list:
    """Gather responses from devices asynchronously when running a multi command."""
    tasks = [get_multi_results(hostname, device, command, raw_only) for hostname, device in devices.items()]
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


async def do_single_lg_command(location: str, command: str, ipaddress: str, raw_only: bool = False) -> dict:
    """Run a looking glass command on a device."""

    cli = get_cmd(location, command, ipaddress)

    try:
        response = await execute_on_device(
            hostname=cli["device"],
            device_type=cli["type"],
            cli_cmds=cli["cmd"],
            timeout=get_command_timeout(command),
        )
    except (ScrapliException, OSError) as err:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing command '{command}' at location '{location}'",
        ) from err

    # Parse output if raw_only is False and a template exists
    parsed_output = []
    if not raw_only and (template_name := get_template(command, cli["type"])):
        parsed_output = await process_response(response.result, template_name, command, LOCATIONS_CFG[location]["type"])
    if not parsed_output:
        raw_only = True

    return {
        "parsed_output": parsed_output,
        "raw_output": response.result,
        "raw_only": raw_only,
        "command": command,
        "location": location,
        "location_name": LOCATIONS_CFG[location]["name"],
    }
