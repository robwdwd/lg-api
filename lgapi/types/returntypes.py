# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Various return types of functions"""
from typing import TypedDict


class CmdResult(TypedDict):
    """Results from execute command"""

    location: str
    device_type: str
    cmd: str


class LocationResult(TypedDict):
    """Location result for multi-commands"""

    result: str
    errors: list[str]


class MultiLocationResult(TypedDict):
    """Location result for multi-commands"""

    location: str
    result: str
    errors: list[str]
