from http.client import OK as HTTP_OK_200

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.test import TestCase

from pytest import mark

from tests.common_tools import template_used
from conference.models import (
    Conference,
    Schedule,
    Event,
    Track,
    EventTrack,
    AttendeeProfile,
)

from . import factories


@mark.django_db
def test_names_are_not_abbreviated(client):
    """
    Based on https://github.com/EuroPython/epcon/issues/778
    """

    conference = Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE
    )

    user = factories.UserFactory(email='joedoe@example.com',
                                      first_name='Joejoe',
                                      last_name='Doedoe',
                                      is_active=True)
    talk = factories.TalkFactory()
    factories.TalkSpeakerFactory(talk=talk, speaker=factories.SpeakerFactory(user=user))

    schedule = Schedule.objects.create(
        conference=conference.name,
        slug='someslug',
        date=timezone.now().date(),
        description='Some Description'
    )

    test_track = Track.objects.create(
        schedule=schedule,
        title='Test Track 1'
    )

    event = Event.objects.create(
        schedule=schedule,
        start_time=timezone.now(),
        talk=talk,
    )
    EventTrack.objects.create(event=event, track=test_track)

    schedule_url = reverse('schedule:schedule')

    response = client.get(schedule_url)
    assert response.status_code == HTTP_OK_200
    assert template_used(response, 'conference/schedule/schedule.html')
    assert 'J. Doedoe' not in response.content.decode()
    assert 'Joejoe Doedoe' in response.content.decode()


class TestView(TestCase):
    def setUp(self):
        self.user = factories.UserFactory(password='password1234', is_superuser=True)
        is_logged = self.client.login(username=self.user.username,
                                      password='password1234')
        self.assertTrue(is_logged)

    def test_p3_schedule_empty(self):
        # When trying to view the schedule and no schedule exists, expect 404
        _ = factories.ConferenceFactory()
        url = reverse('schedule:schedule')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
