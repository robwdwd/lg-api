# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

from typing_extensions import TypeAlias

IPvAnyNetworkOrIPType: TypeAlias = "IPv4Network | IPv6Network | IPv4Address | IPv6Address"
