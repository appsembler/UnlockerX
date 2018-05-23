# -*- coding: utf-8 -*-
"""
unlockerx Django application initialization.
"""

from __future__ import absolute_import, unicode_literals

import logging

from ratelimitbackend.backends import RateLimitMixin

from django.apps import AppConfig
from django.conf import settings

from unlockerx.helpers import update_middlewares

LOGGER = logging.getLogger(__name__)


class UnlockerXConfig(AppConfig):
    """
    Configuration for the unlockerx Django application.
    """

    name = 'unlockerx'

    def ready(self):
        """
        Monkeypatch the AUTHENTICATION_BACKENDS to add UnlockerX's.
        """
        settings.MIDDLEWARE_CLASSES = update_middlewares(settings.MIDDLEWARE_CLASSES)

        RateLimitMixin.minutes = 5
        RateLimitMixin.requests = 100  # Make the limit a little bit more permissive
        LOGGER.warn('Monkeypatching RateLimitMixin.requests to %s for a bit more permissive limit.',
                    RateLimitMixin.requests)
