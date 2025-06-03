# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Device command runner."""
import asyncio

from scrapli import AsyncScrapli
from scrapli.exceptions import ScrapliException
from scrapli.response import MultiResponse, Response

# from lgapi.commands import get_multi_commands
from lgapi.config import settings
from lgapi.types.returntypes import MultiCmdResult

LOCATIONS_CFG = settings.locations

DEFAULT_TIMEOUT = 60
COMMAND_TIMEOUTS = {"traceroute": 600}


def get_command_timeout(command: str) -> int:
    """Get timeout for a specific command."""
    return COMMAND_TIMEOUTS.get(command, DEFAULT_TIMEOUT)


def get_default_args(hostname: str, device_type: str, auth_group: str | None) -> dict:
    """Set up default device arguments."""

    group = settings.authentication.groups.get(auth_group) if auth_group else None
    username = group.username if group else settings.authentication.groups["fallback"].username
    password = group.password if group else settings.authentication.groups["fallback"].password

    return {
        "platform": device_type,
        "host": hostname,
        "auth_strict_key": False,
        "transport": "asyncssh",
        "auth_username": username,
        "auth_password": password,
    }


async def execute_on_device(
    hostname: str,
    device_type: str,
    auth_group: str | None,
    cli_cmds: list[str] | str,
    timeout: int = DEFAULT_TIMEOUT,
) -> MultiResponse | Response:
    """Execute the command(s) on the network device."""
    device = get_default_args(hostname, device_type, auth_group)

    async with AsyncScrapli(**device) as net_connect:
        if isinstance(cli_cmds, str):
            return await net_connect.send_command(command=cli_cmds, timeout_ops=timeout)

        return await net_connect.send_commands(commands=cli_cmds, timeout_ops=timeout)


async def execute_on_devices(hostname: str, device: MultiCmdResult, command: str) -> tuple[str, str]:
    """Run multiple commands on the device and return (location, output)."""
    location = device["location"]

    try:
        response = await execute_on_device(
            hostname=hostname,
            device_type=device["device_type"],
            auth_group=LOCATIONS_CFG[location].authentication,
            cli_cmds=device["cmds"],
            timeout=get_command_timeout(command),
        )

    except (ScrapliException, OSError) as err:
        raise Exception(f"Error getting output for {device['location']}") from err

    raw_output = "\n".join(resp.result for resp in response.data)

    return (location, raw_output)


async def gather_device_results(devices: dict[str, MultiCmdResult], command: str) -> list:
    """Gather responses from devices asynchronously when running a multi command."""
    tasks = [execute_on_devices(hostname, device, command) for hostname, device in devices.items()]
    return await asyncio.gather(*tasks, return_exceptions=True)
