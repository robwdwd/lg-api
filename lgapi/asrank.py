# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Caida AS Rank API client."""
import httpx


async def api(url: str) -> dict:
    """Performs an asynchronous HTTP GET request to the specified URL using an AsyncClient.
    Handles HTTP errors and returns the JSON response data if successful.

    Args:
        url (str): The URL to fetch data from.

    Returns:
        dict: The JSON response data, or an empty dictionary if there is an error or the data is not present.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError:
            return {}

    return {} if "error" in result or "data" not in result else result["data"]


def AsnQuery(asn: int):
    """Format the GraphQL content for retriving the data."""
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


async def asn_to_name(asn: int) -> dict:
    """Map the ASN to a name."""

    async with httpx.AsyncClient() as client:
        try:
            query = AsnQuery(asn)
            response = await client.post(
                "https://api.asrank.caida.org/v2/graphql",
                json={'query': query}
                )
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError:
            return {}

    return {} if "error" in result or "data" not in result or "asn" not in result['data'] else result["data"]['asn']


