# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Device command runner."""
import asyncio
import pprint
from typing import Any, List, Union

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

pp = pprint.PrettyPrinter(indent=2, width=120)

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


async def execute_command(
    hostname: str,
    device_type: str,
    cli_cmds: Union[List[str], str],
    timeout: int = DEFAULT_TIMEOUT,
) -> Union[MultiResponse, Response]:
    """Execute the command(s) on the network device."""
    device = get_default_args(hostname, device_type)

    async with AsyncScrapli(**device) as net_connect:
        if isinstance(cli_cmds, str):
            return await net_connect.send_command(command=cli_cmds, timeout_ops=timeout)

        return await net_connect.send_commands(commands=cli_cmds, timeout_ops=timeout)


async def run_multi(hostname: str, device: dict, command: str, raw_only: bool = False) -> dict:
    """Run commands on device.

    Args:
        hostname (str): Device hostname.
        device (dict): Device dictionary with commands, location, etc.
        raw_only (bool): Do not parse the device output.

    Raises:
        Exception: On failure raise excetion.

    Returns:
        dict: Output from device and device location.
    """
    parsed_output = None
    try:
        response = await execute_command(
            hostname=hostname,
            device_type=device["type"],
            cli_cmds=device["cmds"],
            timeout=60,
        )
        raw_output = "\n".join(resp.result for resp in response.data)

        if not raw_only:
            parsed_output = parse_txt(raw_output, device["template"])[0]

            if command == "bgp":
                parsed_output = await process_bgp_output(parsed_output)
            elif command == "ping":
                parsed_output = await process_ping_output(parsed_output)
            elif command == "traceroute":
                parsed_output = await process_traceroute_output(parsed_output)

    except Exception as err:
        raise Exception(f"Error getting output for {device['location']}: {err}") from err

    return {
        "parsed_output": parsed_output,
        "raw_output": raw_output,
        "location": device["location"],
        "location_name": device["location_name"],
        "raw_only": raw_only,
    }


async def process_responses(responses: list, raw_only: bool = False) -> dict:
    """Process responses and populate the output table."""

    output_table = {"locations": [], "errors": [], "raw_only": raw_only}

    for response in responses:
        if isinstance(response, Exception):
            output_table["errors"].append(str(response))
        else:
            location = response["location"]
            location_name = settings.lg_config["locations"][location]["name"]
            output_table["locations"].append({"name": location_name, "results": response})

    return output_table


async def gather_device_responses(devices: dict[str, Any], command: str, raw_only: bool) -> list:
    """Gather responses from devices asynchronously."""
    tasks = [run_multi(hostname, device, command, raw_only) for hostname, device in devices.items()]
    return await asyncio.gather(*tasks, return_exceptions=True)


async def run_cmd_multi(targets: MultiPingBody | MultiBgpBody, command: str, raw_only: bool = False):
    """Run multiple commands on devices"""
    locations = list(dict.fromkeys(targets.locations))

    # Convert IP list to strings and remove any duplicates
    ipaddresses = list(dict.fromkeys(map(str, targets.destinations)))

    devices = get_multi_commands(locations, ipaddresses, command)

    # Get templates for the devices.
    #
    for device in devices.values():
        template_name = get_template(command, device["type"])
        device["template"] = template_name

        # If any device is missing a template revert back to raw output
        # for all devices.
        if not template_name:
            raw_only = True

    try:
        responses = await gather_device_responses(devices, command, raw_only)
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing multiple {command} commands: {err}",
        ) from err

    return await process_responses(responses, raw_only)


async def run_cmd(location: str, command: str, ipaddress: str, raw_only: bool = False) -> dict:
    """Run a command on a device.
    Args:
        location (str): Location to run command from
        command (str): Command to run
        ipaddress (str): IP address to run command against
        raw_only (bool): Return only raw command output without any parsing

    Returns:
        dict: Command results
    """

    cli = get_cmd(location, command, ipaddress)

    try:
        response = await execute_command(
            hostname=cli["device"],
            device_type=cli["type"],
            cli_cmds=cli["cmd"],
            timeout=get_command_timeout(command),
        )
    except (ScrapliException, OSError) as err:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing command '{command}' at location '{location}': {err}",
        ) from err

    # Parse output if raw_only is False and a template exists
    parsed_output = None
    if not raw_only:
        if template_name := get_template(command, cli["type"]):
            parsed_output = response.ttp_parse_output(template=template_name)[0]

            if command == "bgp":
                parsed_output = await process_bgp_output(parsed_output)
            elif command == "ping":
                parsed_output = await process_ping_output(parsed_output)
            elif command == "traceroute":
                parsed_output = await process_traceroute_output(parsed_output)
        else:
            raw_only = True  # Fallback to only raw output if no template is found

    if not parsed_output:
        raw_only = True

    return {
        "parsed_output": parsed_output,
        "raw_output": response.result,
        "raw_only": raw_only,
        "command": command,
    }
