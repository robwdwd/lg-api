# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Get commands to run on devices."""
import asyncio
import collections
import ipaddress
import pprint

from lgapi import logger
from lgapi.cache import command_key_builder
from lgapi.config import settings
from lgapi.decorators import command_cache
from lgapi.device import execute_on_device, get_command_timeout
from lgapi.types.models import MultiBgpBody, MultiPingBody
from lgapi.types.returntypes import CmdResult, LocationResult, MultiLocationResult

pp = pprint.PrettyPrinter(indent=2, width=120)

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


async def execute_multiple_commands(
    targets: MultiPingBody | MultiBgpBody,
    command: str,
) -> list[MultiLocationResult]:
    """Execute command on device."""

    locations = list(set(targets.locations))
    ipaddresses = list({str(dest) for dest in targets.destinations})

    # Prepare all (location, destination) pairs
    pairs = [(location, destination) for location in locations for destination in ipaddresses]

    # Launch all tasks in parallel
    tasks = [execute_single_command(location, command, destination) for location, destination in pairs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results by location
    location_results: dict[str, LocationResult] = collections.defaultdict(lambda: {"result": "", "errors": []})

    for (location, destination), result in zip(pairs, results):
        if isinstance(result, Exception):
            logger.warning("Error executing %s at %s for %s: %s", command, location, destination, result)
            location_results[location]["errors"].append(
                f"{location}:{destination}: Error getting output from network device"
            )
        elif isinstance(result, str):
            location_results[location]["result"] += result
        else:
            logger.warning("Unexpected result type for %s at %s for %s: %r", command, location, destination, result)
            location_results[location]["errors"].append(
                f"{location}:{destination}: Unexpected result type: {type(result).__name__}"
            )

    # Format final output
    formatted_results: list[MultiLocationResult] = []
    for location, data in location_results.items():
        formatted_results.append({"location": location, "result": data["result"], "errors": data["errors"]})

    return formatted_results


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
