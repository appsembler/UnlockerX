# -*- coding: utf-8 -*-
"""
UnlockerX models to log the issues and allow removing limits.
"""

from __future__ import absolute_import, unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from model_utils.models import TimeStampedModel

from student.models import LoginFailures


@python_2_unicode_compatible
class RateLimitedIP(TimeStampedModel):
    """
    A model to store IP-based ratelimits.
    """

    ip_address = models.GenericIPAddressField(primary_key=True)
    lockout_count = models.IntegerField(default=1, db_index=True)

    # This is informational, which aids search
    # In reality there could be many users for the same model, but I for now
    # need only the latest user.
    latest_user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        if self.latest_user:
            username = self.latest_user.username
        else:
            username = '(no user)'

        return '{ip_address}: {username}'.format(
            ip_address=self.ip_address,
            username=username,
        )

    class Meta:
        """
        Meta for RateLimitedIP model.
        """

        app_label = 'unlockerx'

        # Rename the model and make it a bit more user-friendly.
        verbose_name = 'IP-based Lock'
        verbose_name_plural = 'IP-based Locks'


@python_2_unicode_compatible
class StudentAccountLock(LoginFailures):
    """
    Make a proxy/fake LoginFailures model, to organize the admin panel a bit.

    The name of the model is also adjusted to be user friendly.
    """

    def __str__(self):
        """
        Human friendly name.
        """
        return u'{username} account lock'.format(username=self.user.username)

    class Meta:
        """
        Meta for StudentAccountLock model.
        """

        app_label = 'unlockerx'

        # Prevents generating migrations.
        proxy = True
        managed = False
        auto_created = True
