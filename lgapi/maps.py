# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Filter Gen and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Map communities and ASNs to more human values and other data mapping function."""


import asyncio
import re
import socket
import sqlite3

import aiosqlite

from lgapi.asrank import asn_to_name
from lgapi.config import settings


def init_db():
    """Initialise the mappings database."""

    db_con = sqlite3.connect("mapsdb/maps.db")

    db_cursor = db_con.cursor()
    db_cursor.execute("DROP TABLE IF EXISTS communities")
    db_cursor.execute("CREATE TABLE communities(community, name)")

    records = []

    with open("mapsdb/communities.txt", "r") as communities_file:
        for line in communities_file:
            line = line.strip()
            if line.startswith("#") or not line:
                continue

            data = re.split(r"\s+", line, maxsplit=1)
            if len(data) == 2:
                records.append(data)

    db_cursor.executemany("INSERT INTO communities VALUES(?,?);", records)
    db_con.commit()
    db_con.close()


async def process_bgp_output(output: dict) -> list:
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
                    new_prefix["asn_info"][asn] = await asn_to_name(asn)

                result.append(new_prefix)

    return result


async def process_ping_output(output: dict) -> list:
    """Process the output of the ping command."""

    return [{**destination, "ip_address": ip_address} for ip_address, destination in output.items()]


async def reverse_lookup(ipaddr: str) -> str | None:
    """Do a reverse lookup on an IP address asynchronously."""
    loop = asyncio.get_running_loop()
    try:
        fqdn, _, _ = await loop.run_in_executor(None, socket.gethostbyaddr, ipaddr)
        return fqdn
    except socket.herror:
        return None


async def process_traceroute_output(output: dict) -> list[dict]:
    """Process the output of the traceroute command."""
    resolve_mode = settings.resolve_traceroute_hops

    if resolve_mode in {"missing", "all"}:
        results = []
        for ip_address, data in output.items():
            hops = data["hops"]

            # Prepare tasks for hops that need resolution
            tasks = []
            hop_indices = []
            for idx, hop in enumerate(hops):
                hop_ip = hop.get("ip_address")
                fqdn = hop.get("fqdn")
                if hop_ip and (not fqdn or resolve_mode == "all"):
                    tasks.append(reverse_lookup(hop_ip))
                    hop_indices.append(idx)

            # Run all reverse lookups concurrently
            resolved_fqdns = await asyncio.gather(*tasks) if tasks else []

            # Assign resolved FQDNs back to hops
            for idx, fqdn in zip(hop_indices, resolved_fqdns):
                if fqdn:
                    hops[idx]["fqdn"] = fqdn

            results.append({"ip_address": ip_address, "hops": hops})
        return results

    return [{"ip_address": ip_address, "hops": data["hops"]} for ip_address, data in output.items()]


async def process_location_output_by_region(locations: list[dict]) -> list[dict]:
    """Process the output for location by region API call."""
    result = {}
    for location in locations:
        region = location.get("region", "No Region")
        if region not in result:
            result[region] = {"name": region, "locations": []}
        result[region]["locations"].append(location)

    return list(result.values())
