"""
Tests for the UnlockerX rate limit app.
"""
from __future__ import absolute_import, unicode_literals

from datetime import datetime, timedelta

import ddt
from dateutil.parser import parse as parse_datetime
from mock import Mock, patch
from ratelimitbackend import admin as ratelimitbackend_admin
from ratelimitbackend.backends import RateLimitModelBackend
from ratelimitbackend.exceptions import RateLimitException

from django.conf import settings
from django.contrib.admin import ModelAdmin, site
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from student.tests.factories import UserFactory
from unlockerx import helpers as unlockerx_helpers
from unlockerx.admin import RateLimitedIPAdmin
from unlockerx.middleware import UnlockerXRateLimitMiddleware
from unlockerx.models import RateLimitedIP, StudentAccountLock

EDX_MIDDLEWARE = 'ratelimitbackend.middleware.RateLimitMiddleware'
UNLOCKERX_MIDDLEWARE = 'unlockerx.middleware.UnlockerXRateLimitMiddleware'


class SettingsTest(TestCase):
    """
    Sanity checks for the environment settings.
    """

    def test_middleware_configuration(self):
        """
        Ensures that the middlewares are being updated.
        """
        self.assertIn(UNLOCKERX_MIDDLEWARE, settings.MIDDLEWARE_CLASSES)
        self.assertNotIn(EDX_MIDDLEWARE, settings.MIDDLEWARE_CLASSES)

    def test_ip_ratelimit_settings(self):
        """
        Checks if the IP-based lock configurations reflects the requirements.

        This is important for other tests to pass correctly.

        Changing the value here requires changing the other tests.
        """
        self.assertEquals(RateLimitModelBackend.minutes, 5,
                          msg='Keep the same edX tests, and avoid over-querying the cache')

        self.assertEquals(RateLimitModelBackend.requests, 100,
                          msg='Increase the requests limit per 5 minutes, to avoid locking university students')


@patch('unlockerx.helpers.log_failed_attempt')
class UnlockerXRateLimitMiddlewareTest(TestCase):
    """
    Tests for the database logs of `UnlockerXRateLimitMiddleware`.
    """

    def test_process_normal_exception(self, mock_log):
        obj = UnlockerXRateLimitMiddleware()
        obj.process_exception(Mock(), IndexError())
        mock_log.assert_not_called()

    def test_process_ratelimi_exception(self, mock_log):
        obj = UnlockerXRateLimitMiddleware()
        obj.process_exception(Mock(), RateLimitException('Forbidden', 100))
        assert mock_log.call_count == 1


@ddt.ddt
class AdminSetupTest(TestCase):
    """
    Tests for the admin setup and some logic tests.
    """

    @ddt.data(RateLimitedIP, StudentAccountLock)
    def test_activated_admin_classes(self, model_class):
        """
        Ensure that the admin classes are activated.
        """
        self.assertTrue(site.is_registered(model_class), 'Model should be registered')

    def test_admin_checks(self):
        """
        Catch common pitfals in admin panel configurations.
        """
        ratelimitbackend_admin.autodiscover()
        call_command('check')

    def test_admin_login_limit(self):
        """
        Try (and fail) logging into admin 100 times in a row on an non-existent user.
        """
        cache.clear()

        assert not RateLimitedIP.objects.all(), 'There should be no registered locks!'

        for i in range(100):
            good_resp = self.client.post('/admin/login/', {
                'username': 'thisdoesnotexist{0}'.format(i),
                'password': 'password!',
            })

            assert good_resp.status_code == 200

        for expected_lock_count in [1, 2]:
            # then the rate limiter should kick in and give a HttpForbidden response
            bad_resp = self.client.post('/admin/login/', {
                'username': 'thisdoesnotexist',
                'password': 'password!',
            })

            assert bad_resp.status_code == 403
            assert len(RateLimitedIP.objects.all()) == 1, 'There should be one registered lock!'
            limit = RateLimitedIP.objects.all()[0]
            assert limit.lockout_count == expected_lock_count

        cache.clear()


class FakeRequestTest(TestCase):
    """
    Tests for the FakeRequest class helper.
    """

    def test_ip_address(self):
        """
        Test the ip_address in FakeRequest class.
        """
        ip_address = '8.8.8.8'
        request = unlockerx_helpers.FakeRequest(ip_address=ip_address)
        self.assertEquals(request.META['REMOTE_ADDR'], ip_address)
        self.assertFalse(hasattr(request, 'POST'))

    def test_username(self):
        """
        Test the username in FakeRequest class.
        """
        ip_address = '8.8.8.8'
        request = unlockerx_helpers.FakeRequest(ip_address=ip_address, username='robot')
        self.assertEquals(request.POST['username'], 'robot')


class RateLimitedIPAdminTest(TestCase):
    """
    Testing the custom methods in the RateLimitedIPAdminTest
    """

    def setUp(self):
        """
        Initialize RateLimitedIPAdmin.
        """
        super(RateLimitedIPAdminTest, self).setUp()
        self.admin = RateLimitedIPAdmin(RateLimitedIP, site)

    @patch('unlockerx.admin.humanize_delta')
    def test_custom_list_display_methods(self, humanize_delta_mock):
        """
        Tests `list_display` `lockout_duration` method.
        """

        utc_now = datetime.utcnow()
        self.admin.lockout_duration(Mock(created=utc_now, modified=utc_now))
        self.assertEquals(humanize_delta_mock.call_count, 1, 'humanize_delta should be called once')

    def test_unlock_time(self):
        """
        Tests `unlock_time` method for `list_display`.
        """
        utc_now = parse_datetime('Aug 28 1999 12:05AM')
        dummy_obj = Mock(modified=utc_now)

        utc_after_5 = parse_datetime('Aug 28 1999 12:10AM')

        self.assertEquals(self.admin.unlock_time(dummy_obj), utc_after_5,
                          msg='Unlock date should be 5 minutes after the last failed attempt')

    def test_no_raw_delete(self):
        """
        Raw delete wasn't preventing the deletion of corresponding DB entries, so `reset_attempts` was introduced.
        """
        request_mock = Mock(GET={})

        original_django_actions = ModelAdmin.get_actions(self.admin, request_mock)
        actions = self.admin.get_actions(request_mock)

        self.assertIn('delete_selected', original_django_actions, 'Just making sure we are testing correctly')
        self.assertNotIn('delete_selected', actions,
                         msg='Should be removed')
        self.assertIn('reset_attempts', actions, 'Use `reset_attempts` custom action')

    @patch('unlockerx.admin.cache')
    def test_delete_with_cache_invalidate(self, cache_mock):
        rate_limit_1 = Mock(ip_address='8.8.8.8')
        rate_limit_2 = Mock(ip_address='8.8.4.4')
        self.admin.reset_attempts(request=None, queryset=[rate_limit_1, rate_limit_2])

        self.assertEquals(rate_limit_1.delete.call_count, 1, 'Should delete the object')
        self.assertEquals(rate_limit_2.delete.call_count, 1, 'Should delete the object')
        self.assertEquals(cache_mock.delete_many.call_count, 2, 'Should delete entries of two objects')


@ddt.ddt
class RateLimitedIPTest(TestCase):
    """
    Tests for the RateLimitedIP model.
    """
    def test_str_method_anonymous(self):
        """
        Tests the __str__ magic method for correct admin display.
        """
        ip_address = '1.2.3.4'
        obj = RateLimitedIP(ip_address=ip_address)
        self.assertEquals(str(obj), '{ip_address}: (no user)'.format(ip_address=ip_address))

    def test_str_method_with_user(self):
        ip_address = '8.8.4.4'
        obj = RateLimitedIP(ip_address=ip_address, latest_user=UserFactory(username='ali'))
        self.assertEquals(str(obj), '{ip_address}: ali'.format(ip_address=ip_address))

    @ddt.data('verbose_name', 'verbose_name_plural')
    def test_meta(self, property_name):
        """
        Ensures that the model has user-friendly name in the admin panel.
        """
        property_value = getattr(RateLimitedIP._meta, property_name)  # pylint: disable=protected-access
        self.assertIn('IP-based', property_value)


@ddt.ddt
class HelpersTest(TestCase):
    """
    Tests for unlockerx helpers.
    """
    @ddt.unpack
    @ddt.data(
        {'delta': None, 'output': '0 seconds', 'msg': 'Base case'},
        {'delta': timedelta(seconds=0), 'output': '0 seconds'},
        {'delta': timedelta(seconds=2), 'output': '2 seconds'},
        {'delta': timedelta(days=4, seconds=40), 'output': '4 days'},
        {'delta': timedelta(weeks=5, days=10), 'output': '45 days'},
    )
    def test_humanize_delta_helper(self, delta, output, msg=None):
        """
        Tests the humanize_delta helper.

        Args:
            delta: Mock relative time delta object.
            output: expected string output from the helper.
            msg: optional message to assert statement.
        """
        self.assertEquals(unlockerx_helpers.humanize_delta(delta), output, msg)

    def test_missing_middleware_on_update(self):
        with self.assertRaises(ValueError):
            unlockerx_helpers.update_middlewares(('backend1', 'backend2'))

    def test_update_middlewaress_helper(self):
        """
        Ensures that the helper preserves the middleware location.
        """
        updated_middlewares = unlockerx_helpers.update_middlewares((
            'dummy1',
            EDX_MIDDLEWARE,
            'dummy2',
        ))

        self.assertNotIn(EDX_MIDDLEWARE, updated_middlewares)
        self.assertIn(UNLOCKERX_MIDDLEWARE, updated_middlewares)

        self.assertEquals(1, updated_middlewares.index(UNLOCKERX_MIDDLEWARE),
                          msg='Should have the UlockerX middleware in the same position where the edX middleware was.')

    def test_call_update_middleware_twice(self):
        expected = [UNLOCKERX_MIDDLEWARE]
        assert unlockerx_helpers.update_middlewares([UNLOCKERX_MIDDLEWARE]) == expected

    @ddt.data(
        [EDX_MIDDLEWARE],  # List
        (EDX_MIDDLEWARE,)  # Tuple
    )
    def test_update_middleware(self, middlewares):
        expected = [UNLOCKERX_MIDDLEWARE]
        self.assertEquals(unlockerx_helpers.update_middlewares(middlewares), expected)


class StudentAccountLockTest(TestCase):
    """
    Basic checks to ensure that the model will have no migrations.
    """

    def test_no_migrations(self):
        """
        Check for migrations-related meta properties.
        """
        meta = StudentAccountLock._meta  # pylint: disable=protected-access
        self.assertTrue(meta.auto_created, 'Should not migrate')
        self.assertFalse(meta.managed, 'Should not migrate')

    def test_str_method(self):
        """
        Tests the __str__ magic method for correct admin display.
        """
        user = UserFactory(username='user1')
        obj = StudentAccountLock(user=user)
        self.assertEquals(str(obj), 'user1 account lock')

    @patch('unlockerx.helpers.log_failed_attempt')
    def test_rate_not_exceeded(self, db_log_failed_attempt):
        """
        Testing when the rate limit is not exceeded.
        """
        expected_user = UserFactory()

        # Patch ModelBackend to bypass username and password checks.
        with patch('django.contrib.auth.backends.ModelBackend.authenticate', return_value=expected_user):
            backend = RateLimitModelBackend()

            mock_request = unlockerx_helpers.FakeRequest(ip_address='240.1.3.4')
            authenticated_user = backend.authenticate(username='user1', password='dummy', request=mock_request)

            self.assertIs(expected_user, authenticated_user, 'Should authenticate the user')

            # Ensures that nothing is logged in the database.
            db_log_failed_attempt.assert_not_called()

    def test_db_log_failed_attempt_with_user(self):
        """
        Tests for the UnlockerXRateLimitMixin.db_log_failed_attempt method.
        """
        omar = UserFactory(email='omar@example.com')
        ali = UserFactory(email='ali@example.com')
        omar_fake_request = unlockerx_helpers.FakeRequest(ip_address='150.0.3.31', username=omar.username)

        with self.assertRaises(RateLimitedIP.DoesNotExist):
            RateLimitedIP.objects.get(latest_user=omar)

        unlockerx_helpers.log_failed_attempt(omar_fake_request)

        omar_limit = RateLimitedIP.objects.get(latest_user=omar)

        self.assertEquals(omar_limit.ip_address, '150.0.3.31', 'Should log the entry with correct IP')
        self.assertEquals(omar_limit.lockout_count, 1, 'Only one attempt so far')

        unlockerx_helpers.log_failed_attempt(unlockerx_helpers.FakeRequest(ip_address='150.0.3.31'))

        with self.assertRaises(RateLimitedIP.DoesNotExist):
            # Should clear the user from the record
            RateLimitedIP.objects.get(latest_user=omar)

        # Get the user back
        ali_fake_request = unlockerx_helpers.FakeRequest(ip_address='150.0.3.31', username=ali.username)
        unlockerx_helpers.log_failed_attempt(ali_fake_request)
        ali_limit = RateLimitedIP.objects.get(latest_user=ali)

        assert ali_limit.lockout_count == 3, \
            'Three attempts from the same IP so far, regardless of the user'

    def test_db_log_failed_attempt_anonymous(self):
        """
        Tests for the UnlockerXRateLimitMixin.db_log_failed_attempt for unauthenticated users.
        """
        anonymous_req = unlockerx_helpers.FakeRequest(ip_address='150.0.3.31', username='fake username')
        unlockerx_helpers.log_failed_attempt(anonymous_req)

        limits = RateLimitedIP.objects.all()
        assert len(limits) == 1

        latest_limit = limits[0]

        assert latest_limit.ip_address == '150.0.3.31', 'Should log the entry with correct IP'
        assert latest_limit.lockout_count == 1, 'Only one attempt so far'

        # There should be no user for this record
        assert not latest_limit.latest_user

        omar = UserFactory(email='omar@example.com')  # Authenticated request
        omar_req = unlockerx_helpers.FakeRequest(ip_address='150.0.3.31')
        omar_req.user = omar

        # Log an authenticated user
        unlockerx_helpers.log_failed_attempt(omar_req)
        limits = RateLimitedIP.objects.all()
        assert len(limits) == 1
        omar_limit = limits[0]

        assert omar_limit.lockout_count == 2,  \
            'Two attempts from the same IP so far, regardless of the user'
        assert omar_limit.latest_user.email == 'omar@example.com'

        ali = UserFactory(email='ali@example.com')
        # Assign a different user
        ali_req = unlockerx_helpers.FakeRequest(ip_address='150.0.3.31', username=ali.username)
        unlockerx_helpers.log_failed_attempt(ali_req)
        ali_limit = RateLimitedIP.objects.get(latest_user=ali)

        assert ali_limit.lockout_count == 3,  \
            'Three attempts from the same IP so far, regardless of the user'
