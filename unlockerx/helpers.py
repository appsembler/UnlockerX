"""
UnlockerX ratelimit helpers.
"""

from __future__ import absolute_import, unicode_literals

import logging

from django.contrib.auth.models import User

from unlockerx.models import RateLimitedIP

LOGGER = logging.getLogger(__name__)


class FakeRequest(object):
    """
    A fake request class for tests.
    """

    def __init__(self, ip_address, username=None):
        """
        Provide the fake request object with a META['REMOTE_ADDR'] property.

        Args:
            ip_address: A string IP address e.g. 150.221.45.3
            username: A username to emulate a login request.
        """
        self.META = {  # pylint: disable=invalid-name
            'REMOTE_ADDR': ip_address,
        }

        if username:
            self.POST = {  # pylint: disable=invalid-name
                'username': username,
            }


def log_failed_attempt(request):
    """
    Store information about the failed attempt in the database.

    We're overriding the values to avoid forking ratelimit pip package itself.

    Args:
        request: WSGIRequest object.
    """
    # TODO: Make it safe with a try/catch

    user = None
    ip_address = request.META['REMOTE_ADDR']

    # TODO: Get username from the request

    username = getattr(request, 'POST', {}).get('username')
    if username:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            pass

    if not user:
        if hasattr(request, 'user') and request.user.is_authenticated():
            user = request.user

    limited_ip, created = RateLimitedIP.objects.update_or_create(
        ip_address=ip_address,
        defaults={
            # There could be multiple users, but storing the latest should be fine for
            # our limited intent to use it as information.
            'latest_user': user,
        },
    )

    if not created:
        # TODO: Use `update_or_create((defaults{lockout_count': F('lockout_count')+1})` instead to save a database hit
        # but this is only supported in Django versions > 1.8
        limited_ip.lockout_count += 1
        limited_ip.save()


def update_middlewares(original_middlewares):
    """
    Patche the MIDDLEWARE_CLASSES setting to replace `RateLimitMiddleware` with UnlockerX's.

    Args:
        original_middlewares: the original middleware tuple.
    Return:
        The updated middlewares tuple.
    """
    edx_middleware = 'ratelimitbackend.middleware.RateLimitMiddleware'
    unlockerx_middleware = 'unlockerx.middleware.UnlockerXRateLimitMiddleware'

    if unlockerx_middleware in original_middlewares:
        return original_middlewares

    # TODO: Use proper lms plugins on Open edX Hawthorne release. Maybe it's worth it, may be not!
    LOGGER.warn('Monkeypatching MIDDLEWARE_CLASSES to use the UnlockerX middleware. original=%s',
                original_middlewares)

    # Normalize to a list to work with devstack.py.
    original_middlewares = list(original_middlewares)

    try:
        index = original_middlewares.index(edx_middleware)
    except ValueError:
        LOGGER.error('Open edX middleware "%s" in "%s", this module likely needs an update. ',
                     edx_middleware, original_middlewares)
        raise

    return original_middlewares[:index] + [unlockerx_middleware] + original_middlewares[(index + 1):]


def humanize_delta(delta):
    """
    Provide a more human friendly delta description.

    This helper only cares about the most significant unit e.g.
        - '5 seconds and 3 minutes' will be shown as '3 minutes'
        - '1 years and 5 months' will be shown as '1 years'
        - and so on

    Args:
        delta: relativedelta object.

    Return: str
        '1 years'
        '2 months'
        '20 minutes'
        '1 seconds'
        '0 seconds'
    """
    periods = ('days', 'seconds',)

    for period in periods:
        if hasattr(delta, period):
            count = getattr(delta, period)

            if count:
                return '{count} {period}'.format(
                    count=count,
                    period=period,
                )

    return '0 seconds'
