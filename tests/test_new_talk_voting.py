from datetime import date, timedelta

import pytest

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone

from conference.models import Conference, VotoTalk
from conference.talk_voting import VotingOptions
from conference.tests.factories.speaker import SpeakerFactory
from conference.tests.factories.talk import TalkFactory, TalkSpeakerFactory

pytestmark = [pytest.mark.django_db]


def _setup(start=date(2019, 7, 8), end=date(2019, 7, 14)):
    # Create a conference with talk voting enabled
    Conference.objects.get_or_create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_NAME,
        conference_start=start,
        conference_end=end,
        voting_start=timezone.now() - timedelta(days=3),
        voting_end=timezone.now() + timedelta(days=3),
    )


@pytest.mark.xfail
def test_talk_voting_unavailable_if_not_enabled():
    assert True == False


@pytest.mark.xfail
def test_talk_voting_unavailable_without_a_ticket():
    assert True == False


@pytest.mark.xfail
def test_talk_voting_available_with_ticket_and_enabled():
    assert True == False


@pytest.mark.xfail
def test_talk_voting_filters():
    assert True == False


@pytest.mark.xfail
def test_talk_voting_hides_admin_talks():
    assert True == False


@pytest.mark.xfail
def test_talk_voting_hides_approved_talks():
    assert True == False


def test_vote_submission(user_client):
    _setup()
    talk = TalkFactory()

    url = reverse("talk_voting:vote", kwargs={'talk_uuid': talk.uuid})

    user_client.post(url, data={'vote': VotingOptions.maybe})

    assert VotoTalk.objects.count() == 1


def test_vote_submission_not_allowed_for_own_talk(user_client):
    _setup()
    talk = TalkFactory()
    speaker = SpeakerFactory(user=user_client.user)
    TalkSpeakerFactory(talk=talk, speaker=speaker)

    url = reverse("talk_voting:vote", kwargs={'talk_uuid': talk.uuid})

    user_client.post(url, data={'vote': VotingOptions.maybe})

    assert VotoTalk.objects.count() == 0


@pytest.mark.xfail
def test_talk_voting_creates_new_vote():
    assert True == False
