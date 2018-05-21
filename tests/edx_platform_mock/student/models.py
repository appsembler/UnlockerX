from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.db import models


class LoginFailures(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    failure_count = models.IntegerField(default=0)
    lockout_until = models.DateTimeField(null=True)

    class Meta:
        app_label = 'student'
