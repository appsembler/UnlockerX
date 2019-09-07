"""
Admin panel to report the ratelimits and allow cancelling them.
"""

from __future__ import absolute_import, unicode_literals

import datetime

import six
from dateutil.relativedelta import relativedelta
from ratelimitbackend.backends import RateLimitModelBackend

from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.core.cache import cache

from unlockerx.helpers.helpers import FakeRequest, humanize_delta
from unlockerx.models import RateLimitedIP, StudentAccountLock


class RateLimitedIPAdmin(admin.ModelAdmin):
    """
    Admin for RateLimitedIP model.
    """

    actions = ['reset_attempts']

    readonly_fields = (
        'ip_address',
        'latest_user',
        'created',
        'modified',
        'lockout_count',
    )

    list_display = (
        'display_name',
        'latest_user',
        'lockout_count',
        'lockout_duration',
        'unlock_time',
        'created',
        'modified',
    )

    search_fields = (
        'ip_address',
        'latest_user__username',
        'latest_user__email',
    )

    list_filter = (
        ('modified', DateFieldListFilter),
    )

    ordering = ('-modified',)

    def lockout_duration(self, obj):
        """
        Return a human friendly duration.
        """
        delta = relativedelta(obj.modified, obj.created)
        return humanize_delta(delta)

    def display_name(self, obj):
        """
        Text representation of the RateLimitedIP object.
        """
        return six.text_type(obj)

    def unlock_time(self, obj):
        """
        Calculate the nearest time to unlock the authenticate attempts.
        """
        unlock_duration = datetime.timedelta(minutes=RateLimitModelBackend.minutes)
        return obj.modified + unlock_duration

    def get_actions(self, request):
        """
        Remove Django's `delete_selected` in order to use `reset_attempts` instead.
        """
        actions = super(RateLimitedIPAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def reset_attempts(self, request, queryset):
        """
        Reset attemps action in the admin dropdown.
        """
        for obj in queryset:
            self.delete_model(request, obj)

    def delete_model(self, request, obj):
        """
        Delete a model and reset it's attempts in the cache.
        """
        backend = RateLimitModelBackend()
        cache_keys = backend.keys_to_check(request=FakeRequest(obj.ip_address))
        cache.delete_many(cache_keys)
        obj.delete()


class StudentAccountLockAdmin(admin.ModelAdmin):
    """
    An admin for the `StudentAccountLock` admin.
    """

    search_fields = (
        'user__email', 'user__username', 'user__pk',
    )

    readonly_fields = (
        'user', 'failure_count', 'lockout_until',
    )

    list_display = (
        'email', 'username', 'failure_count', 'lockout_until',
    )

    def email(self, login_failures):
        """
        Provide the user email for the admin list.
        """
        return login_failures.user.email

    def username(self, login_failures):
        """
        Provide the username for the admin list.
        """
        return login_failures.user.username


admin.site.register(StudentAccountLock, StudentAccountLockAdmin)
admin.site.register(RateLimitedIP, RateLimitedIPAdmin)
