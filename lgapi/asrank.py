# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Caida AS Rank API client."""
from aiocache import cached
from httpx import AsyncClient, HTTPError


def get_graphql_query(asn: int) -> str:
    """Format the GraphQL query for retrieving the ASN data."""
    return f"""{{
        asn(asn:"{asn}") {{
            asnName
            rank
            organization {{
                orgName
            }}
            country {{
                iso
                name
            }}
        }}
    }}"""


@cached(ttl=3600, alias="default")
async def asn_to_name(asn: int, httpclient: AsyncClient) -> dict:
    """Map the ASN to a name."""

    try:
        query = get_graphql_query(asn)
        response = await httpclient.post(
            "https://api.asrank.caida.org/v2/graphql",
            json={"query": query},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        asn_data = result.get("data", {}).get("asn")
        return asn_data if asn_data else {}
    except HTTPError:
        return {}
