# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Get commands to run on devices."""

import ipaddress

from fastapi import HTTPException
from scrapli.exceptions import ScrapliException

from lgapi.config import settings
from lgapi.datamodels import MultiBgpBody, MultiPingBody
from lgapi.device import execute_on_device, gather_device_results, get_command_timeout

LOCATIONS_CFG = settings.lg_config["locations"]
COMMANDS_CFG = settings.lg_config["commands"]


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

    cli_cmd = COMMANDS_CFG[command][device_type][ip_version].replace("IPADDRESS", ip_address)

    if command != "bgp" and source:
        cli_cmd = cli_cmd.replace("SOURCE", source)

    return cli_cmd


def get_multi_commands(locations: list[str], ip_addresses: list[str], command: str) -> dict[str, dict]:
    """Get commands and devices types to run based on location and ip addresses."""
    command_list: dict[str, dict] = {}

    for location in locations:
        loc_cfg = LOCATIONS_CFG[location]
        device = loc_cfg["device"]
        device_type = loc_cfg["type"]
        source = loc_cfg.get("source")

        cli_cmds = [build_cli_cmd(command, device_type, ip_address, source) for ip_address in ip_addresses]

        command_list[device] = {
            "location": location,
            "type": device_type,
            "cmds": cli_cmds,
        }

    return command_list


def get_cmd(location: str, command: str, ip_address: str) -> dict[str, str]:
    """Get command to run on device."""
    loc_cfg = LOCATIONS_CFG[location]
    return {
        "device": loc_cfg["device"],
        "type": loc_cfg["type"],
        "cmd": build_cli_cmd(command, loc_cfg["type"], ip_address, loc_cfg.get("source")),
    }


async def execute_multiple_commands(
    targets: MultiPingBody | MultiBgpBody,
    command: str,
) -> list[dict[str, str]]:
    """Execute command on device."""

    locations = list(set(targets.locations))
    ipaddresses = list(set(map(str, targets.destinations)))
    device_commands = get_multi_commands(locations, ipaddresses, command)

    try:
        device_output = await gather_device_results(device_commands, command)
        
        return [{"location": location, "result": result} for location, result in device_output]
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing multiple {command} commands: {err}",
        ) from err


async def execute_single_command(location: str, command: str, destination: str) -> str:
    """Execute command on device."""

    device_commands = get_cmd(location, command, destination)

    try:
        response = await execute_on_device(
            hostname=device_commands["device"],
            device_type=device_commands["type"],
            cli_cmds=device_commands["cmd"],
            timeout=get_command_timeout(command),
        )
        return response.result
    except (ScrapliException, OSError) as err:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing command '{command}' at location '{location}'",
        ) from err
