# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""TTP Template helper functions."""

from pathlib import Path

from ttp import ttp


def parse_txt(raw_output: str, template: str) -> list[dict[str, dict]]:
    """Parse raw device output with ttp template.

    Args:
        raw_output (str): Raw output from network device
        template (str): Filename of TTP template for this device and output

    Returns:
        list[dict[str, dict]: TTP parsed structure or empty list if unable to parse
    """
    try:
        ttp_parser = ttp(data=raw_output, template=template)
        ttp_parser.parse()
        return ttp_parser.result(structure="flat_list")
    except Exception:
        return []


def get_template(command: str, device_type: str) -> str | None:
    """Get TTP Template file name.

    Returns:
        Template filename or None if file not found.
    """
    template_path = Path("lgapi/ttp_templates") / f"{device_type}_{command}.ttp"
    return str(template_path) if template_path.is_file() else None
