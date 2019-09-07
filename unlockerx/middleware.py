"""
Open edX authentication backends with custom rate limits.
"""

from __future__ import absolute_import, unicode_literals

from ratelimitbackend.middleware import RateLimitMiddleware

from django.http import HttpResponseForbidden

from unlockerx.helpers import helpers as unlockerx_helpers


class UnlockerXRateLimitMiddleware(RateLimitMiddleware):
    """
    Handles exceptions thrown by rate-limited login attepmts.
    """

    def process_exception(self, request, exception):
        """
        Log the ratelimited exceptions in the database.
        """
        response = super(UnlockerXRateLimitMiddleware, self).process_exception(request, exception)

        if response and isinstance(response, HttpResponseForbidden):
            unlockerx_helpers.log_failed_attempt(request)

        return response
