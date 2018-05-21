# -*- coding: utf-8 -*-
"""
URLs for unlockerX.
"""
from __future__ import absolute_import, unicode_literals

from ratelimitbackend import admin

from django.conf.urls import include, url

admin.autodiscover()

urlpatterns = (
    url(r'^admin/', include(admin.site.urls)),
)
