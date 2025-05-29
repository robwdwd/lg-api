# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Process output from the routers into the correct structures."""


import asyncio
import collections
import re

import aiosqlite
import dns.asyncresolver
import dns.reversename
from aiocache import cached
from httpx import AsyncClient

from lgapi import logger
from lgapi.asrank import asn_to_name
from lgapi.cache import ip_key_builder
from lgapi.config import settings
from lgapi.cymru import cymru_ip_to_asn


async def process_bgp_output(output: dict, httpclient: AsyncClient) -> list:
    """Process the output of the BGP command."""
    result = []

    async with aiosqlite.connect("mapsdb/maps.db") as db_con:
        async with db_con.cursor() as db_cursor:
            # Collect all communities to batch-fetch their descriptions
            # Fetch community descriptions in one query
            if all_communities := {
                community
                for prefix in output
                for path in output[prefix]["paths"]
                for community in path.get("communities", [])
            }:
                placeholders = ",".join("?" for _ in all_communities)
                sql = f"SELECT community, name FROM communities WHERE community IN ({placeholders})"
                res = await db_cursor.execute(sql, tuple(all_communities))
                community_map = {row[0]: row[1] for row in await res.fetchall()}
            else:
                community_map = {}

            for prefix in output:
                new_prefix = {"prefix": prefix, "paths": [], "as_paths": []}
                as_path_list = []

                for path in output[prefix]["paths"]:
                    # Parse AS path
                    if aspath := path.get("as_path"):
                        parsed_aspath = [int(asp) for asp in aspath.split() if asp.isnumeric()]
                        path["as_path"] = parsed_aspath
                        as_path_list.append(parsed_aspath)

                    # Map communities
                    if communities := path.get("communities"):
                        path["communities"] = [
                            {"community": community, "description": community_map.get(community)}
                            for community in communities
                        ]

                    new_prefix["paths"].append(path)

                # Deduplicate and sort AS paths
                new_prefix["as_paths"] = [list(path) for path in {tuple(path) for path in as_path_list if path}]
                unique_asns = list({asn for path in new_prefix["as_paths"] for asn in path})
                new_prefix["asn_info"] = {}
                for asn in unique_asns:
                    new_prefix["asn_info"][asn] = await asn_to_name(asn, httpclient)

                result.append(new_prefix)

    return result


async def process_ping_output(output: dict) -> list:
    """Process the output of the ping command."""

    return [{**destination, "ip_address": ip_address} for ip_address, destination in output.items()]


@cached(ttl=3600, alias="default", key_builder=ip_key_builder)
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


async def process_junos_hops(hops: list):
    """Process JunOS traceroute hops"""
    probe_regex = re.compile(
        r"^(?:(?P<fqdn>[\w\.-]+) \((?P<ip>(?:\d{1,3}\.){3}\d{1,3}|(?:[a-fA-F0-9:]+:+)+[a-fA-F0-9]+)\)"
        r"|(?P<ip_only>(?:\d{1,3}\.){3}\d{1,3}|(?:[a-fA-F0-9:]+:+)+[a-fA-F0-9]+))?\s*(?P<rtt>\d+\.\d+)?$"
    )

    flat_hops = []
    for hop in hops:
        hop_number = str(hop["hop_number"])
        probes = hop["probes"]
        segments = [seg.strip() for seg in probes.split("ms") if seg.strip()]
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

            m = probe_regex.match(seg)
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
                resolved_fqdns = dict(zip(ip_to_indices, lookup_results))

                # Assign resolved FQDNs back to hops
                for ip, indices in ip_to_indices.items():
                    fqdn = resolved_fqdns.get(ip)
                    if fqdn:
                        for idx in indices:
                            hops[idx]["fqdn"] = fqdn

        # --- ASN info for all hops with IPs ---
        all_ips = {hop.get("ip_address") for hop in hops if hop.get("ip_address")}
        if all_ips:
            cymru_infos = await asyncio.gather(*(cymru_ip_to_asn(ip) for ip in all_ips))
            cymru_results = dict(zip(all_ips, cymru_infos))
            for hop in hops:
                ip = hop.get("ip_address")
                if ip:
                    hop["info"] = cymru_results.get(ip)

            # --- ASRank info for all unique ASNs found in cymru_results ---
            unique_asns = {
                info["asn"]
                for info in cymru_results.values()
                if info and "asn" in info and info["asn"]
            }

            asrank_results = {}
            if unique_asns:
                asrank_infos = await asyncio.gather(*(asn_to_name(asn, httpclient) for asn in unique_asns))
                asrank_results = dict(zip(unique_asns, asrank_infos))

            # Attach ASRank info to each hop if ASN is present
            for hop in hops:
                asn = hop.get("info", {}).get("asn")
                if asn:
                    hop["info"]["asrank"] = asrank_results.get(asn)

        results.append({"ip_address": ip_address, "hops": hops})

    return results


async def process_location_output_by_region(locations: list[dict]) -> list[dict]:
    """Process the output for location by region API call."""
    result = {}
    for location in locations:
        region = location.get("region", "No Region")
        if region not in result:
            result[region] = {"name": region, "locations": []}
        result[region]["locations"].append(location)

    return list(result.values())
