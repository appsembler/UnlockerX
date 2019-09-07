"""
Common settings for both lms and studio.
"""
from __future__ import absolute_import, unicode_literals

from unlockerx.helpers.settings_helpers import update_middlewares


def plugin_settings(settings):
    """
    Enable the UnlockerX customizations for all environments.
    """
    settings.MIDDLEWARE_CLASSES = update_middlewares(settings.MIDDLEWARE_CLASSES)
