# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Get commands to run on devices."""

import ipaddress

from aiocache import cached
from fastapi import HTTPException
from scrapli.exceptions import ScrapliException

from lgapi import logger
from lgapi.cache import command_key_builder
from lgapi.config import settings
from lgapi.device import execute_on_device, gather_device_results, get_command_timeout
from lgapi.types.models import MultiBgpBody, MultiPingBody
from lgapi.types.returntypes import CmdResult, MultiCmdResult

LOCATIONS_CFG = settings.locations
COMMANDS_CFG = settings.commands


def get_ip_version(ip: str) -> str:
    """Return 'ipv4' or 'ipv6' based on the IP address or CIDR."""
    try:
        net = ipaddress.ip_network(ip, strict=False)
        return "ipv4" if net.version == 4 else "ipv6"
    except ValueError:
        return "ipv4"


def build_cli_cmd(command: str, device_type: str, ip_address: str, source: str | None = None) -> str:
    """Build the CLI command string."""
    ip_version = get_ip_version(ip_address)

    command_cfg = getattr(COMMANDS_CFG, command)
    device_cfg = command_cfg[device_type]
    cli_cmd = getattr(device_cfg, ip_version).replace("IPADDRESS", ip_address)

    if command != "bgp" and source:
        cli_cmd = cli_cmd.replace("SOURCE", source)

    return cli_cmd


def get_multi_commands(locations: list[str], ip_addresses: list[str], command: str) -> dict[str, MultiCmdResult]:
    """Get commands and devices types to run based on location and ip addresses."""
    command_list: dict[str, MultiCmdResult] = {}

    for location in locations:
        loc_cfg = LOCATIONS_CFG[location]
        cli_cmds = [build_cli_cmd(command, loc_cfg.type, ip_address, loc_cfg.source) for ip_address in ip_addresses]

        command_list[loc_cfg.device] = {
            "location": location,
            "device_type": loc_cfg.type,
            "cmds": cli_cmds,
        }

    return command_list


def get_cmd(location: str, command: str, ip_address: str) -> CmdResult:
    """Get command to run on device."""
    loc_cfg = LOCATIONS_CFG[location]
    return {
        "location": location,
        "device_type": loc_cfg.type,
        "cmd": build_cli_cmd(command, loc_cfg.type, ip_address, loc_cfg.source),
    }


async def execute_multiple_commands(
    targets: MultiPingBody | MultiBgpBody,
    command: str,
) -> list[dict[str, str]]:
    """Execute command on device."""

    locations = list(set(targets.locations))
    ipaddresses = list({str(dest) for dest in targets.destinations})
    device_commands = get_multi_commands(locations, ipaddresses, command)

    try:
        device_output = await gather_device_results(device_commands, command)

        results = [
            {
                "location": location,
                "error": "Error getting output from network device",
            } if isinstance(result, Exception) else {
                "location": location,
                "result": result,
            }
            for location, result in device_output
        ]
        return results

    except Exception as err:
        logger.warning("Error executing multi-%s: %s", command, err)
        raise HTTPException(
            status_code=500,
            detail=f"Error executing multi-{command} command",
        ) from err

@cached(ttl=60, alias="default", key_builder=command_key_builder)
async def execute_single_command(location: str, command: str, destination: str) -> str:
    """Execute command on device."""

    logger.debug("Cache Miss: Execute %s command at %s to %s", command, location, destination)

    device_commands = get_cmd(location, command, destination)
    loc_config = LOCATIONS_CFG[location]

    try:
        response = await execute_on_device(
            hostname=loc_config.device,
            device_type=device_commands["device_type"],
            cli_cmds=device_commands["cmd"],
            auth_group=loc_config.authentication,
            timeout=get_command_timeout(command),
        )
        return response.result
    except (ScrapliException, OSError) as err:
        logger.warning(
            "Error getting device output from '%s' (%s) for command '%s': %s", loc_config.device, location, command, err
        )

        raise HTTPException(
            status_code=500,
            detail=f"Error executing command '{command}' at location '{loc_config.name}'",
        ) from err
