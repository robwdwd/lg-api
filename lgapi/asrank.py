# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Caida AS Rank API client."""
from aiocache import cached
from httpx import AsyncClient, HTTPError


def get_graphql_query(asn: int):
    """Format the GraphQL query for retriving the ASN data."""
    return """{
        asn(asn:"%i") {
            asnName
            rank
            organization {
                orgName
            }
            country {
                iso
                name
            }
        }
    }""" % (
        asn
    )


@cached(ttl=3600, alias="default")
async def asn_to_name(asn: int, httpclient: AsyncClient) -> dict:
    """Map the ASN to a name."""

    try:
        query = get_graphql_query(asn)
        response = await httpclient.post("https://api.asrank.caida.org/v2/graphql", json={"query": query})
        response.raise_for_status()
        result = response.json()
    except HTTPError:
        return {}

    return {} if "error" in result or "data" not in result or "asn" not in result["data"] else result["data"]["asn"]
