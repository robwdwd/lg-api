# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
import ipaddress

import dns.asyncresolver
from aiocache import cached

from lgapi import logger
from lgapi.cache import asn_key_builder, ip_key_builder


@cached(ttl=3600, alias="default", key_builder=ip_key_builder)
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
            except ValueError:
                return None

        asn = get_part(0)
        result = {
            "asn": asn,
            "bgp_prefix": get_part(1),
            "registry": get_part(3),
        }

        # If ASN is present, get more info from ASN DNS interface
        if asn and asn.isdigit():
            asn_info = await cymru_get_asn(asn)
            if asn_info:
                result.update(asn_info)

        return result
    except Exception as e:
        logger.debug('Unable to map IP to ASN: %s', str(e))
        return {}


@cached(ttl=3600, alias="default", key_builder=asn_key_builder)
async def cymru_get_asn(asn: str) -> dict:
    """Get ASN details from Cymru"""
    logger.debug("Cache Miss: Cymru ASN lookup: %s", asn)
    try:
        resolver = dns.asyncresolver.Resolver()

        asn_query = f"AS{asn}.asn.cymru.com"
        asn_answer = await resolver.resolve(asn_query, "TXT")
        asn_parts = [p.strip() for p in asn_answer[0].to_text().strip('"').split("|")]

        def get_asn_part(idx):
            try:
                return asn_parts[idx]
            except ValueError:
                return None

        return {"as_name": get_asn_part(4), "as_cc": get_asn_part(1)}
    except Exception as e:
        logger.debug('Unable to get ASN details: %s', str(e))
        return {}
