# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Process bgp output from the routers into the correct structures."""


import asyncio

from httpx import AsyncClient

from lgapi.database import get_community_map
from lgapi.processing.asrank import get_asn_information


async def process_bgp_output(output: dict, httpclient: AsyncClient) -> list:
    """Process the output of the BGP command."""
    result = []

    all_communities = set()
    all_asns = set()

    # Collect all unique communities and assets
    for prefix in output.values():
        for path in prefix["paths"]:
            aspath = path.get("as_path", "")
            parsed_aspath = [int(asp) for asp in aspath.split() if asp.isnumeric()]
            path["as_path"] = parsed_aspath
            all_asns.update(parsed_aspath)
            all_communities.update(path.get("communities", []))

    community_map = await get_community_map(all_communities)
    asn_info_result = await asyncio.gather(*(get_asn_information(asn, httpclient) for asn in all_asns))

    asn_infos = dict(zip(all_asns, asn_info_result))

    for prefix, prefix_data in output.items():
        new_prefix = {"prefix": prefix, "paths": [], "as_paths": []}
        as_path_set = set()

        for path in prefix_data["paths"]:
            aspath = path.get("as_path")
            if aspath:
                as_path_set.add(tuple(aspath))

            # Map communities
            communities = path.get("communities")
            if communities:
                path["communities"] = [
                    {"community": community, "description": community_map.get(community)} for community in communities
                ]

            new_prefix["paths"].append(path)

        # Deduplicate and sort AS paths for this prefix only.
        new_prefix["as_paths"] = [list(path) for path in as_path_set if path]
        unique_asns = {asn for path in new_prefix["as_paths"] for asn in path}
        new_prefix["asn_info"] = {asn: asn_infos[asn] for asn in unique_asns if asn in asn_infos}

        result.append(new_prefix)

    return result
