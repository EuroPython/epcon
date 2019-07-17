from datetime import timedelta
from unittest import mock

import pytest
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone

from conference.models import Conference, VotoTalk, TALK_STATUS
from conference.talk_voting import VotingOptions, find_talks
from tests.factories import SpeakerFactory, TalkFactory, TalkSpeakerFactory
from tests.common_tools import make_user, create_talk_for_user, get_default_conference

pytestmark = [pytest.mark.django_db]


@pytest.mark.xfail
def test_talk_voting_unavailable_if_not_enabled():
    assert False


@pytest.mark.xfail
def test_talk_voting_unavailable_without_a_ticket():
    assert False


@pytest.mark.xfail
def test_talk_voting_available_with_ticket():
    assert False


def test_talk_voting_available_with_proposal(user_client):
    get_default_conference()
    create_talk_for_user(user=user_client.user)
    url = reverse("talk_voting:talks")

    response = user_client.get(url)

    assert response.status_code == 200


@pytest.mark.xfail
def test_talk_voting_vote_filters():
    assert False


@pytest.mark.xfail
def test_talk_voting_type_filters():
    assert False


@pytest.mark.xfail
def test_talk_voting_both_filters():
    assert False


@pytest.mark.xfail
def test_talk_voting_hides_admin_talks():
    assert False


@pytest.mark.xfail
def test_talk_voting_hides_approved_talks():
    assert False


def test_vote_submission(user_client):
    get_default_conference()
    talk = TalkFactory()
    speaker = SpeakerFactory(user=make_user())
    TalkSpeakerFactory(talk=talk, speaker=speaker)

    url = reverse("talk_voting:vote", kwargs={'talk_uuid': talk.uuid})

    user_client.post(url, data={'vote': VotingOptions.maybe})

    assert VotoTalk.objects.count() == 1


def test_vote_submission_not_allowed_for_talk_created_by_user(user_client):
    get_default_conference()
    # User is speaker but did not create the talk
    talk = TalkFactory(status=TALK_STATUS.proposed)
    speaker = SpeakerFactory(user=user_client.user)
    TalkSpeakerFactory(talk=talk, speaker=speaker)

    url = reverse("talk_voting:vote", kwargs={'talk_uuid': talk.uuid})

    user_client.post(url, data={'vote': VotingOptions.maybe})

    assert VotoTalk.objects.count() == 0


def test_vote_submission_not_allowed_for_talk_where_user_is_speaker(user_client):
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.proposed, created_by=user_client.user)

    url = reverse("talk_voting:vote", kwargs={'talk_uuid': talk.uuid})

    user_client.post(url, data={'vote': VotingOptions.maybe})

    assert VotoTalk.objects.count() == 0


def test_dont_vote_talks_without_speaker_details(db, user_client):
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.proposed)

    url = reverse("talk_voting:vote", kwargs={'talk_uuid': talk.uuid})

    user_client.post(url, data={'vote': VotingOptions.maybe})

    assert VotoTalk.objects.count() == 0


def test_vote_talks_with_speaker_details(db, user_client):
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.proposed)

    speaker = SpeakerFactory(user=make_user())
    TalkSpeakerFactory(talk=talk, speaker=speaker)

    url = reverse("talk_voting:vote", kwargs={'talk_uuid': talk.uuid})

    user_client.post(url, data={'vote': VotingOptions.maybe})

    assert VotoTalk.objects.count() == 1


@mock.patch('conference.talk_voting.is_user_allowed_to_vote', return_value=True)
def test_dont_publish_talks_without_speaker_details(db, user_client, mocker):
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.proposed, title="DeadBeef")
    talk2 = TalkFactory(status=TALK_STATUS.proposed, title="TestProposalForTests")
    speaker = SpeakerFactory(user=make_user())
    TalkSpeakerFactory(talk=talk2, speaker=speaker)

    url = reverse("talk_voting:talks")

    response = user_client.get(url)

    assert talk.title not in response.content.decode("utf8")
    assert talk2.title in response.content.decode("utf8")


def test_dont_publish_talks_without_speaker_details1(db, user_client, mocker):
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.proposed, title="DeadBeef")
    talk2 = TalkFactory(status=TALK_STATUS.proposed, title="TestProposalForTests")
    speaker = SpeakerFactory(user=make_user())
    TalkSpeakerFactory(talk=talk2, speaker=speaker)

    talks = find_talks(user_client.user, Conference.objects.current(), [])
    assert talk not in talks

    assert talk2 in talks
