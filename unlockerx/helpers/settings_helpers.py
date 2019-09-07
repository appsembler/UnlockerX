"""
UnlockerX ratelimit helpers for settings.

Using a separate module to avoid circular dependencies.
"""
from __future__ import absolute_import, unicode_literals

import logging

LOGGER = logging.getLogger(__name__)


def update_middlewares(original_middlewares):
    """
    Edit the MIDDLEWARE_CLASSES setting to replace `RateLimitMiddleware` with UnlockerX's.

    Args:
        original_middlewares: the original middleware tuple.
    Return:
        The updated middlewares tuple.
    """
    edx_middleware = 'ratelimitbackend.middleware.RateLimitMiddleware'
    unlockerx_middleware = 'unlockerx.middleware.UnlockerXRateLimitMiddleware'

    if unlockerx_middleware in original_middlewares:
        return original_middlewares

    # Normalize to a list to work with devstack.py.
    original_middlewares = list(original_middlewares)

    try:
        index = original_middlewares.index(edx_middleware)
    except ValueError:
        LOGGER.error('Open edX middleware "%s" in "%s", this module likely needs an update. ',
                     edx_middleware, original_middlewares)
        raise

    return original_middlewares[:index] + [unlockerx_middleware] + original_middlewares[(index + 1):]
