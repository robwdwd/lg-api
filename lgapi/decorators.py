# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Decorator overrides for AIOCache so that caching can be disabled or enabled"""
from functools import wraps
from typing import Any, Callable

from aiocache import cached

from lgapi.config import settings


def command_cache(alias: str, key_builder: Callable) -> Callable:
    """Apply command caching if enabled in settings, otherwise run uncached."""

    cache_enabled = getattr(settings.cache, "enabled", False)
    command_cache_enabled = getattr(getattr(settings.cache, "commands", {}), "enabled", False)
    ttl = getattr(getattr(settings.cache, "commands", {}), "ttl", 180)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if cache_enabled and command_cache_enabled:
            return cached(alias=alias, key_builder=key_builder, ttl=ttl)(func)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def request_cache(alias: str, ttl: int, key_builder: Callable) -> Callable:
    """Apply request caching if enabled in settings, otherwise run uncached."""

    cache_enabled = getattr(settings.cache, "enabled", False)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if cache_enabled:
            return cached(alias=alias, key_builder=key_builder, ttl=ttl)(func)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator
