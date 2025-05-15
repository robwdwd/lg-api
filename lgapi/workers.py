# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
"""Custom Uvicorn worker class.

Create Uvicorn Custom worker for running Uvicorn through Gunicorn
but still allowing a sub path with the root_path setting.
"""

from uvicorn.workers import UvicornWorker

from lgapi.config import settings


class CustomWorker(UvicornWorker):
    """Custom Uvicorn Worker.

    Args:
        UvicornWorker (UvicornWorker): Uvicorn Worker

    """

    CONFIG_KWARGS = {"root_path": settings.root_path, "log_level": settings.log_level, "proxy_headers": True}
