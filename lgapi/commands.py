# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Get commands to run on devices."""

from lgapi.config import settings


def get_multi_commands(locations: list[str], ip_addresses: list[str], command: str) -> dict:
    """Get commands and devices types to run based on location and ip addresses.

    Args:
        locations (list): List of locations to run from
        ip_addresses (list): List of destination IP addresses or networks

    Returns:
        dict: Devices and commands table
    """
    command_list = {}

    for location in locations:
        cli_cmds = []
        device = settings.lg_config["locations"][location]["device"]
        device_type = settings.lg_config["locations"][location]["type"]
        source = settings.lg_config["locations"][location]["source"]
        location_name = settings.lg_config["locations"][location]["name"]

        for ip_address in ip_addresses:
            cli_cmd = settings.lg_config["commands"][command][device_type].replace("IPADDRESS", ip_address)
            if command != "bgp":
                cli_cmd = cli_cmd.replace("SOURCE", source)

            cli_cmds.append(cli_cmd)

            command_list[device] = {"location": location, "location_name": location_name, "type": device_type, "cmds": cli_cmds}

    return command_list


def get_cmd(location: str, command: str, ip_address: str):
    """Get command to run on devices after user submits looking glass form.

    Args:
        location (str): Location user selected
        command (str): Command user selected (bgp, ping, traceroute)
        ip (str): IP or CIDR user entered

    Returns:
        dict: Device, type of device and cli commands to run
    """
    device = settings.lg_config["locations"][location]["device"]
    device_type = settings.lg_config["locations"][location]["type"]
    source = settings.lg_config["locations"][location]["source"]

    cli_cmd = settings.lg_config["commands"][command][device_type].replace("IPADDRESS", ip_address)
    if command != "bgp":
        cli_cmd = cli_cmd.replace("SOURCE", source)

    return {"device": device, "type": device_type, "cmd": cli_cmd}
