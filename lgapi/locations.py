# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
from lgapi.config import LocationConfig


def get_locations(locations: dict[str, LocationConfig]) -> list[dict[str, str]]:
    """Get a list of locations from config file."""
    return [
        {
            "code": code,
            "name": location.name,
            "region": location.region,
        }
        for code, location in locations.items()
    ]


async def get_locations_by_region(locations: dict[str, LocationConfig]) -> list[dict]:
    """Process the output for location by region API call using the Location model."""
    result = {}
    for code, location in locations.items():
        region = location.region or "No Region"
        if region not in result:
            result[region] = {"name": region, "locations": []}
        result[region]["locations"].append({
            "code": code,
            "name": location.name,
            "region": location.region,
        })
    return list(result.values())