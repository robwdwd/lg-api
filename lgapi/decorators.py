# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
from functools import wraps
from typing import Any, Callable

from aiocache import cached

from lgapi.config import settings


def command_cache(alias: str, key_builder: Callable) -> Callable:
    """Conditionally apply command caching based on settings."""

    def decorator(func: Callable) -> Callable:
        # Check if cache is enabled and command cache is enabled
        if settings.cache.enabled and settings.cache.commands.enabled:
            return cached(alias=alias, key_builder=key_builder, ttl=settings.cache.commands.ttl)(func)
        else:
            # Return the function unchanged (no caching)
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                return await func(*args, **kwargs)

            return wrapper

    return decorator


def request_cache(alias: str, ttl: int, key_builder: Callable) -> Callable:
    """Conditionally apply external API request caching based on settings."""

    def decorator(func: Callable) -> Callable:
        if settings.cache.enabled:
            return cached(alias=alias, key_builder=key_builder, ttl=ttl)(func)
        else:

            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                return await func(*args, **kwargs)

            return wrapper

    return decorator
