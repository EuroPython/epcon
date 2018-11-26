# coding: utf-8

from http.client import OK as HTTP_OK_200

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone

from pytest import mark

from tests.common_tools import template_used  # , serve_response
from conference.models import (
    Conference,
    Schedule,
    Event,
    Track,
    EventTrack,
    AttendeeProfile,
)

from django_factory_boy import auth as auth_factories

from assopy.tests.factories.user import AssopyUserFactory
from conference.tests.factories.talk import TalkFactory, TalkSpeakerFactory
from conference.tests.factories.speaker import SpeakerFactory
from p3.tests.factories.talk import P3TalkFactory


@mark.django_db
def test_names_are_not_abbreviated(client):
    """
    Based on https://github.com/EuroPython/epcon/issues/778
    """

    conference = Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE
    )

    user = auth_factories.UserFactory(email='joedoe@example.com',
                                      first_name='Joejoe',
                                      last_name='Doedoe',
                                      is_active=True)
    AssopyUserFactory(user=user)
    talk = TalkFactory()
    AttendeeProfile.objects.getOrCreateForUser(user=user)
    TalkSpeakerFactory(talk=talk, speaker=SpeakerFactory(user=user))
    P3TalkFactory(talk=talk)

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

    schedule_url = reverse(
        'p3-schedule',
        kwargs={'conference': conference.code}
    )

    response = client.get(schedule_url)
    assert response.status_code == HTTP_OK_200
    assert template_used(response, 'p3/schedule.html')
    assert 'J. Doedoe' not in response.content.decode('utf-8')
    assert 'Joejoe Doedoe' in response.content.decode('utf-8')

    list_url = reverse(
        'p3-schedule-list',
        kwargs={'conference': conference.code}
    )

    response = client.get(list_url)
    assert response.status_code == HTTP_OK_200
    assert 'J. Doedoe' not in response.content.decode('utf-8')
    assert 'Joejoe Doedoe' in response.content.decode('utf-8')
    assert template_used(response, 'p3/schedule_list.html')

    # test name abbreviations in ical output
    ical_url = reverse(
        'p3-schedule-ics',
        kwargs={'conference': conference.code}
    )

    # Currently we have neither in the ical version...
    # FIXME(?) https://github.com/EuroPython/epcon/issues/800
    response = client.get(ical_url)
    assert response.status_code == HTTP_OK_200
    assert response['Content-Type'] == 'text/calendar'
    assert 'J. Doedoe' not in response.content.decode('utf-8')
    assert 'Joejoe Doedoe' not in response.content.decode('utf-8')
