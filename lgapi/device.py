# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Device command runner."""


from scrapli import AsyncScrapli
from scrapli.response import Response

from lgapi.config import settings

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
    cli_command: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> Response:
    """Execute the command(s) on the network device."""
    device = get_default_args(hostname, device_type, auth_group)

    async with AsyncScrapli(**device) as net_connect:
        return await net_connect.send_command(command=cli_command, timeout_ops=timeout)
