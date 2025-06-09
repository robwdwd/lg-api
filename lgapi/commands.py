# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Get commands to run on devices."""
import asyncio
import ipaddress

from lgapi import logger
from lgapi.cache import command_key_builder
from lgapi.config import settings
from lgapi.decorators import command_cache
from lgapi.device import execute_on_device, get_command_timeout
from lgapi.types.models import MultiBgpBody, MultiPingBody
from lgapi.types.returntypes import CmdResult, LocationResult

LOCATIONS_CFG = settings.locations
COMMANDS_CFG = settings.commands


def get_ip_version(ip: str) -> str:
    """Return 'ipv4' or 'ipv6' based on the IP address or CIDR."""
    try:
        net = ipaddress.ip_network(ip, strict=False)
        return "ipv4" if net.version == 4 else "ipv6"
    except ValueError:
        return "ipv4"


def build_cli_cmd(command: str, location: str, ip_address: str) -> str:
    """Build the CLI command string."""
    ip_version = get_ip_version(ip_address)
    loc_config = LOCATIONS_CFG[location]
    command_cfg = getattr(COMMANDS_CFG, command)

    device_type = loc_config.type

    device_cfg = command_cfg[device_type]

    cli_cmd = getattr(device_cfg, ip_version).replace("IPADDRESS", ip_address)

    if command != "bgp":
        source = getattr(loc_config.source, ip_version)
        cli_cmd = cli_cmd.replace("SOURCE", source)

    return cli_cmd


def get_cmd(location: str, command: str, ip_address: str) -> CmdResult:
    """Get command to run on device."""
    loc_cfg = LOCATIONS_CFG[location]
    return {
        "location": location,
        "device_type": loc_cfg.type,
        "cmd": build_cli_cmd(command, location, ip_address),
    }


@command_cache(alias="default", key_builder=command_key_builder)
async def execute_single_command(location: str, command: str, destination: str) -> str:
    """Execute command on device."""

    logger.debug("Cache Miss: Execute %s command at %s to %s", command, location, destination)

    device_commands = get_cmd(location, command, destination)
    loc_config = LOCATIONS_CFG[location]

    response = await execute_on_device(
        hostname=loc_config.device,
        device_type=device_commands["device_type"],
        cli_command=device_commands["cmd"],
        auth_group=loc_config.authentication,
        timeout=get_command_timeout(command),
    )
    return response.result


async def run_for_location(
    location: str,
    command: str,
    ipaddresses: list[str],
) -> LocationResult:
    """Run all destinations for a location sequentially."""
    result: LocationResult = {"location": location, "result": "", "errors": []}
    for destination in ipaddresses:
        try:
            cmd_result = await execute_single_command(location, command, destination)
            if result["result"]:
                result["result"] += "\n"
            result["result"] += cmd_result
        except Exception as err:
            logger.warning("Error executing %s at %s for %s: %s", command, location, destination, err)
            result["errors"].append(f"{location}:{destination}: Error getting output from network device")
    return result


async def execute_multiple_commands(
    targets: MultiPingBody | MultiBgpBody,
    command: str,
) -> list[LocationResult]:
    """Execute command on device: destinations per location sequential, locations in parallel."""

    locations = list(set(targets.locations))
    ipaddresses = list({str(dest) for dest in targets.destinations})

    # Run each location in parallel, but destinations per location sequentially
    tasks = [run_for_location(location, command, ipaddresses) for location in locations]
    formatted_results = await asyncio.gather(*tasks, return_exceptions=False)
    return formatted_results
