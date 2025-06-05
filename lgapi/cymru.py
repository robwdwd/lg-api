# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Cymru Network Team lookups"""
import ipaddress

import dns.asyncresolver

from lgapi import logger
from lgapi.cache import ip_key_builder
from lgapi.decorators import request_cache


@request_cache(ttl=3600, alias="default", key_builder=ip_key_builder)
async def cymru_ip_to_asn(ip: str) -> dict:
    """Query Team Cymru's IP-to-ASN DNS interface for info about an IP."""
    logger.debug("Cache Miss: Cymru IP to ASN lookup: %s", ip)
    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.version == 4:
            reversed_ip = ".".join(reversed(ip.split(".")))
            query = f"{reversed_ip}.origin.asn.cymru.com"
        else:
            nibbles = ip_obj.exploded.replace(":", "")
            reversed_nibbles = ".".join(reversed(nibbles))
            query = f"{reversed_nibbles}.origin6.asn.cymru.com"

        resolver = dns.asyncresolver.Resolver()
        answer = await resolver.resolve(query, "TXT")
        parts = [p.strip() for p in answer[0].to_text().strip('"').split("|")]

        def get_part(idx):
            try:
                return parts[idx]
            except IndexError:
                return None

        asn = get_part(0)
        result = {
            "asn": int(asn) if asn and asn.isdigit() else None,
            "bgp_prefix": get_part(1),
            "registry": get_part(3),
        }

        return result
    except Exception as e:
        logger.debug("Unable to map IP to ASN: %s", str(e))
        return {}
