import unittest

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test import override_settings
from django_factory_boy import auth as auth_factories

from conference.tests.factories.attendee_profile import AttendeeProfileFactory
from conference.tests.factories.conference import ConferenceFactory
from p3.tests.factories.schedule import ScheduleFactory


class TestWhosComing(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory(password='password1234', is_superuser=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        AttendeeProfileFactory(user=self.user)
        self.assertTrue(is_logged)

    @override_settings(CONFERENCE_CONFERENCE='epbeta', DEBUG=False)
    def test_p3_whos_coming_no_conference(self):
        url = reverse('p3-whos-coming')
        conference = ConferenceFactory(code='epbeta')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('p3-whos-coming-conference', kwargs={
            'conference': conference.pk,
        }))

    def test_p3_whos_coming_with_conference(self):
        # p3-whos-coming-conference -> p3.views.whos_coming
        # FIXME: The conference parameter has a default value to None, but the url does not accept a empty value
        conference = ConferenceFactory(code='epbeta')
        url = reverse('p3-whos-coming-conference', kwargs={
            'conference': conference.pk
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # FIXME: Test the query string speaker, tags, country


class TestView(TestCase):
    def setUp(self):
        self.user = auth_factories.UserFactory(password='password1234', is_superuser=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        AttendeeProfileFactory(user=self.user)
        self.assertTrue(is_logged)

    def test_p3_billing_with_no_user_cart(self):
        # p3-billing -> p3.views.cart.billing
        url = reverse('p3-billing')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('p3-cart'), fetch_redirect_response=False)

    def test_p3_billing_no_ticket(self):
        # p3-billing -> p3.views.cart.billing
        url = reverse('p3-billing')
        response = self.client.get(url)
        self.assertRedirects(response, reverse('p3-cart'), fetch_redirect_response=False)

    @override_settings(DEBUG=False)
    def test_p3_calculator_get_default_values(self):
        # p3-calculator -> p3.views.cart.calculator
        url = reverse('p3-calculator')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('content-type'), 'application/json')
        self.assertJSONEqual(response.content, {'tickets': [], 'coupon': 0, 'total': 0})

    @override_settings(CONFERENCE='epbeta', CONFERENCE_CONFERENCE='epbeta')
    def test_p3_my_schedule(self):
        # p3-my-schedule -> p3.views.schedule.jump_to_my_schedule
        conference = ConferenceFactory(code='epbeta')

        url = reverse('p3-my-schedule')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        redirect_url = reverse('p3-schedule-my-schedule', kwargs={
            'conference': conference.code
        })

        self.assertRedirects(response, redirect_url, fetch_redirect_response=False)

    @override_settings(CONFERENCE='epbeta')
    def test_p3_schedule_ics(self):
        # p3-schedule-ics -> p3.views.schedule.schedule_ics
        conference = ConferenceFactory(code='epbeta')

        url = reverse('p3-schedule-ics', kwargs={
            'conference': conference.code,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_p3_schedule(self):
        # p3-schedule -> p3.views.schedule.schedule
        conference = ConferenceFactory()
        url = reverse('p3-schedule', kwargs={
            'conference': conference.code
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    # @unittest.skip("FIXME")
    def test_p3_schedule_list(self):
        # p3-schedule-list -> p3.views.schedule.schedule_list
        conference = ConferenceFactory()
        schedule = ScheduleFactory(conference=conference.code)

        url = reverse('p3-schedule-list', kwargs={
            'conference': conference.code,
        })
        response = self.client.get(url)

        values = response.context['sids'].values()

        dict_of_schedule = {
            'conference': schedule.conference,
            'date': schedule.date.date(),
            'description': schedule.description,
            'id': schedule.id,
            'slug': schedule.slug,
        }

        self.assertDictEqual(values[0], dict_of_schedule)
        self.assertEqual(response.status_code, 200)
    
    @unittest.skip("FIXME")
    def test_p3_schedule_my_schedule(self):
        # p3-schedule-my-schedule -> p3.views.schedule.my_schedule
        url = reverse('p3-schedule-my-schedule')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @unittest.skip("FIXME")
    def test_p3_sprint_submission(self):
        # p3-sprint-submission -> p3.views.sprint_submission
        url = reverse('p3-sprint-submission')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @unittest.skip("FIXME")
    def test_p3_sprints(self):
        # p3-sprints -> p3.views.sprints
        url = reverse('p3-sprints')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @unittest.skip("FIXME")
    def test_p3_sprint(self):
        # p3-sprint -> p3.views.sprint
        url = reverse('p3-sprint')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @unittest.skip("FIXME")
    def test_p3_tickets(self):
        # p3-tickets -> p3.views.tickets
        url = reverse('p3-tickets')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @unittest.skip("FIXME")
    def test_p3_ticket(self):
        # p3-ticket -> p3.views.ticket
        url = reverse('p3-ticket')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    @unittest.skip("FIXME")
    def test_p3_user(self):
        # p3-user -> p3.views.user
        url = reverse('p3-user')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @override_settings(CONFERENCE='epbeta')
    def test_p3_schedule_my_schedule_ics(self):
        # p3-schedule-my-schedule-ics -> p3.views.schedule.schedule_ics

        conference = ConferenceFactory(code='epbeta')

        url = reverse('p3-schedule-my-schedule-ics', kwargs={
            'conference': conference.code,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('content-type'), 'text/calendar')

    @override_settings(CONFERENCE='epbeta')
    def test_p3_schedule_my_schedule_ics_error_404(self):
        # p3-schedule-my-schedule-ics -> p3.views.schedule.schedule_ics
        self.client.logout()
        conference = ConferenceFactory(code='epbeta')

        url = reverse('p3-schedule-my-schedule-ics', kwargs={
            'conference': conference.code,
        })
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 404)
