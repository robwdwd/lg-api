# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""TTP Template helper functions."""

from os.path import isfile
from typing import Any, List, Union

from ttp import ttp


def parse_txt(raw_output: str, template: str) -> Union[str, List[Any]]:
    """Parse raw device output with ttp template.

    Args:
        raw_output (str): Raw output from network device
        template (str): Filename of TTP template for this device and output

    Returns:
        Union[str, List[Any]]: TTP parsed structure or raw device output
    """
    try:
        ttp_parser = ttp(data=raw_output, template=template)
        ttp_parser.parse()
        result = ttp_parser.result(structure="flat_list")
        return result
    except Exception:
        return raw_output


def get_template(command: str, device_type: str) -> Union[str, None]:
    """Get TTP Template file name.

    Args:
        command (str): Command to run
        device_type (str): Device Type

    Returns:
        Union[str, None]: Template filename or None if file not found
    """
    template_name = f"lgapi/ttp_templates/{device_type}_{command}.ttp"

    if not isfile(template_name):
        return None

    return template_name
