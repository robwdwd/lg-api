# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Filter Gen and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
import ipaddress

import dns.asyncresolver
from aiocache import cached


@cached(ttl=3600)
async def cymru_ip_to_asn(ip: str) -> dict | None:
    """Query Team Cymru's IP-to-ASN DNS interface for info about an IP."""
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
        txt = answer[0].to_text().strip('"')
        parts = [p.strip() for p in txt.split("|")]

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
            asn_query = f"AS{asn}.asn.cymru.com"
            asn_answer = await resolver.resolve(asn_query, "TXT")
            asn_txt = asn_answer[0].to_text().strip('"')
            asn_parts = [p.strip() for p in asn_txt.split("|")]

            def get_asn_part(idx):
                try:
                    return asn_parts[idx]
                except ValueError:
                    return None

            result["as_name"] = get_asn_part(4)
            result["as_cc"] = get_asn_part(1)
        else:
            result["as_name"] = None
            result["as_cc"] = None

        return result
    except Exception:
        return None
