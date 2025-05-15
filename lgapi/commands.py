# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Get commands to run on devices."""

from lgapi.config import settings


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
        loc_cfg = settings.lg_config["locations"][location]
        device = loc_cfg["device"]
        device_type = loc_cfg["type"]
        source = loc_cfg["source"]
        location_name = loc_cfg["name"]

        cli_cmds = []
        for ip_address in ip_addresses:
            cli_cmd = settings.lg_config["commands"][command][device_type].replace("IPADDRESS", ip_address)
            if command != "bgp":
                cli_cmd = cli_cmd.replace("SOURCE", source)

            cli_cmds.append(cli_cmd)

        command_list[device] = {
            "location": location,
            "location_name": location_name,
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
    loc_cfg = settings.lg_config["locations"][location]
    device = loc_cfg["device"]
    device_type = loc_cfg["type"]
    source = loc_cfg["source"]

    cli_cmd = settings.lg_config["commands"][command][device_type].replace("IPADDRESS", ip_address)
    if command != "bgp":
        cli_cmd = cli_cmd.replace("SOURCE", source)

    return {"device": device, "type": device_type, "cmd": cli_cmd}
