# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Resolve DNS queries."""

import dns.asyncresolver
import dns.reversename

from lgapi import logger
from lgapi.cache import reverse_dns_key_builder
from lgapi.decorators import request_cache


@request_cache(ttl=3600, alias="default", key_builder=reverse_dns_key_builder)
async def reverse_lookup(ipaddr: str) -> str | None:
    """Do a reverse lookup on an IP address asynchronously using DNS."""
    logger.debug("Cache Miss: Reverse DNS lookup %s", ipaddr)
    try:
        resolver = dns.asyncresolver.Resolver()
        rev_name = dns.reversename.from_address(ipaddr)
        answer = await resolver.resolve(rev_name, "PTR")
        return str(answer[0]).rstrip(".")
    except Exception:
        return None
