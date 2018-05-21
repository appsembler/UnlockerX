"""
An app to manage (and remove) password and IP-based locks.

This module depends on `ENABLE_MAX_FAILED_LOGIN_ATTEMPTS` feature for the student-based locks to be enabled.

Introduces three enhancements over the original Open edX ratelimited backend:
 - Loosen up the limits on IP to allow more room of error for university students
   since they usually connect from the same IP.
 - Logs the IP-based ratelimit issues in the database.
 - Shows an admin page for both user and IP based lock  and allow clearing those limit.
"""


from __future__ import absolute_import, unicode_literals

__version__ = '0.1.0'

default_app_config = 'unlockerx.apps.UnlockerXConfig'  # pylint: disable=invalid-name
