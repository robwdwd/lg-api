# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Generate cache keys, used as key builder functions"""


def asn_key_builder(func, *args, **kwargs):
    """Builds the cache key from function name plus the ASN"""
    return f"{func.__name__}:{args[0]}"


def ip_key_builder(func, *args, **kwargs):
    """Builds the cache key from function name plus the destination IP address"""
    return f"{func.__name__}:{args[0]}"


def command_key_builder(func, *args, **kwargs):
    """Builds the cache key from function name plus the command, location and destination IP address"""
    return f"{func.__name__}:{args[0]}_{args[1]}_{args[2]}"
