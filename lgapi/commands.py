# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Get commands to run on devices."""

import ipaddress

from lgapi.config import settings

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

    cli_cmd_template = COMMANDS_CFG[command][device_type][ip_version]
    cli_cmd = cli_cmd_template.replace("IPADDRESS", ip_address)

    if command != "bgp" and source:
        cli_cmd = cli_cmd.replace("SOURCE", source)

    return cli_cmd


def get_multi_commands(locations: list[str], ip_addresses: list[str], command: str) -> dict[str, dict]:
    """Get commands and devices types to run based on location and ip addresses.

    Args:
        locations (list): List of locations to run from
        ip_addresses (list): List of destination IP addresses or networks
        command (str): Command to run (e.g., 'bgp', 'ping', 'traceroute')

    Returns:
        dict[str, dict]: Devices and commands table
    """
    command_list: dict[str, dict] = {}

    for location in locations:
        loc_cfg = LOCATIONS_CFG[location]
        device = loc_cfg["device"]
        device_type = loc_cfg["type"]
        source = loc_cfg.get("source")

        cli_cmds = [build_cli_cmd(command, device_type, ip_address, source) for ip_address in ip_addresses]

        command_list[device] = {
            "location": location,
            "location_name": loc_cfg["name"],
            "type": device_type,
            "cmds": cli_cmds,
        }

    return command_list


def get_cmd(location: str, command: str, ip_address: str) -> dict[str, str]:
    """Get command to run on device.

    Args:
        location (str): Location user selected
        command (str): Command user selected (bgp, ping, traceroute)
        ip_address (str): IP or CIDR user entered

    Returns:
        dict[str, str]: Device, type of device, and CLI command to run
    """
    loc_cfg = LOCATIONS_CFG[location]
    device = loc_cfg["device"]
    device_type = loc_cfg["type"]
    source = loc_cfg.get("source")

    cli_cmd = build_cli_cmd(command, device_type, ip_address, source)

    return {"device": device, "type": device_type, "cmd": cli_cmd}
