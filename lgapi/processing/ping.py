# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Process ping output from the routers into the correct structures."""


async def process_ping_output(output: dict) -> list:
    """Process the output of the ping command."""

    return [{**destination, "ip_address": ip_address} for ip_address, destination in output.items()]
