# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""TTP Template helper functions and parsing."""

from pathlib import Path

from httpx import AsyncClient
from ttp import ttp

from lgapi.config import settings
from lgapi.processing.bgp import process_bgp_output
from lgapi.processing.ping import process_ping_output
from lgapi.processing.traceroute import process_traceroute_output
from lgapi.types.returntypes import MultiLocationResult

LOCATIONS_CFG = settings.locations


def parse_txt(raw_output: str, template: str) -> list[dict[str, dict]]:
    """Parse raw device output with ttp template."""
    try:
        ttp_parser = ttp(data=raw_output, template=template)

        ttp_parser.parse()
        return ttp_parser.result(structure="flat_list")
    except Exception:
        return []


def get_template(command: str, device_type: str) -> str | None:
    """Get TTP Template file name."""
    template_path = Path("lgapi/ttp_templates") / f"{device_type}_{command}.ttp"
    return str(template_path) if template_path.is_file() else None


async def parse_command_output(
    location: str,
    result: str,
    command: str,
    raw: bool = False,
    httpclient: AsyncClient | None = None,
) -> dict:
    """Create standardized command result structure"""
    location_info = LOCATIONS_CFG[location]

    base_result = {
        "parsed_output": [],
        "raw_output": result,
        "raw_only": raw,
        "command": command,
        "location": location,
        "location_name": location_info.name,
    }

    if raw:
        return base_result

    template_name = get_template(command, location_info.type)
    if not template_name:
        base_result["raw_only"] = True
        return base_result

    parsed_result = parse_txt(result, template_name)
    if not isinstance(parsed_result, list) or not parsed_result or not parsed_result[0]:
        base_result["raw_only"] = True
        return base_result

    # Process based on command type
    parsed_output = []
    if command == "ping":
        parsed_output = await process_ping_output(parsed_result[0])
    elif command == "traceroute" and httpclient:
        parsed_output = await process_traceroute_output(parsed_result[0], location_info.type, httpclient)
    elif command == "bgp" and httpclient:
        parsed_output = await process_bgp_output(parsed_result[0], httpclient)

    base_result["parsed_output"] = parsed_output
    base_result["raw_only"] = not parsed_output

    return base_result


async def parse_multi_command_results(
    results: list[MultiLocationResult],
    command: str,
    raw: bool = False,
    httpclient: AsyncClient | None = None,
) -> dict:
    """Process results from multiple command executions"""
    output_table = {"locations": [], "errors": [], "raw_only": raw}

    for result in results:
        if "errors" in result and result["errors"]:
            for err in result["errors"]:
                output_table["errors"].append(f"{result['location']}: {err}")

        if "result" in result and result["result"]:
            parsed_result = await parse_command_output(
                location=result["location"],
                result=result["result"],
                command=command,
                raw=raw,
                httpclient=httpclient,
            )

            location_name = LOCATIONS_CFG[result["location"]].name
            output_table["locations"].append({"name": location_name, "results": parsed_result})

    return output_table
