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
