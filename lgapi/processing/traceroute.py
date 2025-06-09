# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Process traceroute output from the routers into the correct structures."""


import asyncio
import collections
import re

from httpx import AsyncClient

from lgapi.config import settings
from lgapi.processing.asrank import get_asn_information
from lgapi.processing.cymru import ip_to_asn
from lgapi.resolver import reverse_lookup

PROBE_REGEX = re.compile(
    r"^(?:(?P<fqdn>[\w\.-]+) \((?P<ip>(?:\d{1,3}\.){3}\d{1,3}|(?:[a-fA-F0-9:]+:+)+[a-fA-F0-9]+)\)"
    r"|(?P<ip_only>(?:\d{1,3}\.){3}\d{1,3}|(?:[a-fA-F0-9:]+:+)+[a-fA-F0-9]+))?\s*(?P<rtt>\d+\.\d+)?$"
)


async def process_junos_hops(hops: list):
    """Process JunOS traceroute hops"""

    flat_hops = []
    for hop in hops:
        hop_number = str(hop["hop_number"])
        segments = [seg.strip() for seg in hop["probes"].split("ms") if seg.strip()]
        last_fqdn = None
        last_ip = None

        for seg in segments:
            timeout_count = seg.count("*")
            for _ in range(timeout_count):
                flat_hops.append({"hop_number": hop_number, "ip_address": None, "rtt": "*", "fqdn": None})
                hop_number = None  # Only set hop_number for the first probe in this hop
            seg = seg.replace("*", "").strip()
            if not seg:
                continue

            m = PROBE_REGEX.match(seg)
            if m:
                fqdn = m.group("fqdn")
                ip = m.group("ip") or m.group("ip_only")
                rtt = m.group("rtt")
                if fqdn == ip:
                    fqdn = None
                if ip and rtt:
                    flat_hops.append(
                        {"hop_number": hop_number, "ip_address": ip, "rtt": f"{float(rtt):g} msec", "fqdn": fqdn}
                    )
                    hop_number = None
                elif rtt and last_ip:
                    flat_hops.append(
                        {
                            "hop_number": hop_number,
                            "ip_address": last_ip,
                            "rtt": f"{float(rtt):g} msec",
                            "fqdn": last_fqdn,
                        }
                    )
                    hop_number = None
                if ip:
                    last_ip = ip
                    last_fqdn = fqdn

    # Now combine consecutive entries with the same IP
    combined = []
    for entry in flat_hops:
        if combined and entry["ip_address"] == combined[-1]["ip_address"] and entry["fqdn"] == combined[-1]["fqdn"]:
            # Combine RTTs
            combined[-1]["rtt"] += f" {entry['rtt']}"
            # If this entry is a timeout, preserve it
            if entry["rtt"] == "*":
                combined[-1]["rtt"] += ""
        else:
            combined.append(entry)

    # Set hop_number to None except for the first occurrence of each original hop
    last_hop_number = None
    for entry in combined:
        if entry["hop_number"] == last_hop_number:
            entry["hop_number"] = None
        else:
            last_hop_number = entry["hop_number"]

    return combined


async def process_traceroute_output(output: dict, device_type: str, httpclient: AsyncClient) -> list[dict]:
    """Process the output of the traceroute command."""
    resolve_mode = settings.resolve_traceroute_hops
    results = []

    for ip_address, data in output.items():
        hops = data["hops"]

        if device_type == "juniper_junos":
            hops = await process_junos_hops(hops)

        # Prepare tasks for hops that need resolution, avoid duplicate lookups
        if resolve_mode in {"missing", "all"}:
            ip_to_indices = collections.defaultdict(list)
            for idx, hop in enumerate(hops):
                hop_ip = hop.get("ip_address")
                fqdn = hop.get("fqdn")
                if hop_ip and (not fqdn or resolve_mode == "all"):
                    ip_to_indices[hop_ip].append(idx)

            # Run all reverse lookups concurrently (unique IPs only)
            if ip_to_indices:
                lookup_results = await asyncio.gather(*(reverse_lookup(ip) for ip in ip_to_indices))
                for ip, fqdn in zip(ip_to_indices, lookup_results):
                    if fqdn:
                        for idx in ip_to_indices[ip]:
                            hops[idx]["fqdn"] = fqdn

        # --- ASN info for all hops with IPs ---
        all_ips = {hop.get("ip_address") for hop in hops if hop.get("ip_address")}
        if all_ips:
            cymru_infos = await asyncio.gather(*(ip_to_asn(ip) for ip in all_ips))
            cymru_results = dict(zip(all_ips, cymru_infos))
            for hop in hops:
                ip = hop.get("ip_address")
                if ip:
                    hop["info"] = cymru_results.get(ip)

            # --- ASRank info for all unique ASNs found in cymru_results ---
            unique_asns = {info["asn"] for info in cymru_results.values() if info and "asn" in info and info["asn"]}
            if unique_asns:
                asrank_infos = await asyncio.gather(*(get_asn_information(asn, httpclient) for asn in unique_asns))
                asrank_results = dict(zip(unique_asns, asrank_infos))
                for hop in hops:
                    asn = hop.get("info", {}).get("asn")
                    if asn:
                        hop["info"]["asrank"] = asrank_results.get(asn)

        results.append({"ip_address": ip_address, "hops": hops})

    return results
