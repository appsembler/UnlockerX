# -*- coding: utf-8 -*-
"""
unlockerx Django application initialization.
"""
from __future__ import absolute_import, unicode_literals

import logging

from django.apps import AppConfig

LOGGER = logging.getLogger(__name__)


class UnlockerXConfig(AppConfig):
    """
    Configuration for the unlockerx Django application.
    """

    name = 'unlockerx'

    plugin_app = {
        'settings_config': {
            'cms.djangoapp': {
                'common': {
                    'relative_path': 'settings.common',
                },
            },
            'lms.djangoapp': {
                'common': {
                    'relative_path': 'settings.common',
                },
            }
        },
    }

    def ready(self):
        """
        Monkeypatch the RateLimitMixin to add UnlockerX's.
        """
        from ratelimitbackend.backends import RateLimitMixin  # Importing locally to avoid run-time errors.
        RateLimitMixin.minutes = 5
        RateLimitMixin.requests = 100  # Make the limit a little bit more permissive
        LOGGER.warn('Monkeypatching RateLimitMixin.requests to %s for a bit more permissive limit.',
                    RateLimitMixin.requests)
