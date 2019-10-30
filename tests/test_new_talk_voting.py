from datetime import timedelta
from unittest import mock

import pytest
from django.core.urlresolvers import reverse
from django.utils import timezone

from conference.models import Conference, VotoTalk, TALK_STATUS, TALK_TYPE_CHOICES, TALK_ADMIN_TYPE
from conference.talk_voting import VotingOptions, find_talks
from tests.factories import SpeakerFactory, TalkFactory, TalkSpeakerFactory, TicketFactory
from tests.common_tools import make_user, create_talk_for_user, get_default_conference, template_used

pytestmark = [pytest.mark.django_db]


def test_talk_voting_unavailable_before_talk_voting_start(user_client):
    get_default_conference(voting_start=timezone.now() + timedelta(days=1))
    url = reverse('talk_voting:talks')

    response = user_client.get(url)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/talk_voting/voting_is_closed.html")


def test_talk_voting_unavailable_after_talk_voting_end(user_client):
    get_default_conference(voting_end=timezone.now() - timedelta(days=1))
    url = reverse('talk_voting:talks')

    response = user_client.get(url)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/talk_voting/voting_is_closed.html")


def test_talk_voting_unavailable_without_a_ticket(user_client):
    get_default_conference()
    url = reverse('talk_voting:talks')

    response = user_client.get(url)

    assert response.status_code == 200
    assert not user_client.user.ticket_set.exists()
    assert template_used(response, "ep19/bs/talk_voting/voting_is_unavailable.html")


def test_talk_voting_available_with_ticket(user_client):
    get_default_conference()
    TicketFactory(user=user_client.user)
    url = reverse('talk_voting:talks')

    response = user_client.get(url)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/talk_voting/voting.html")


def test_talk_voting_available_with_proposal(user_client):
    get_default_conference()
    create_talk_for_user(user=user_client.user)
    url = reverse("talk_voting:talks")

    response = user_client.get(url)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/talk_voting/voting.html")


@mock.patch('conference.talk_voting.is_user_allowed_to_vote', return_value=True)
def test_talk_voting_lists_proposed_talks(mock_allowed_to_vote, user_client):
    get_default_conference()
    url = reverse("talk_voting:talks")
    talk = create_talk_for_user(user=None, type=TALK_TYPE_CHOICES.t_30)
    training = create_talk_for_user(user=None, type=TALK_TYPE_CHOICES.r_180)
    poster = create_talk_for_user(user=None, type=TALK_TYPE_CHOICES.i_60)
    helpdesk = create_talk_for_user(user=None, type=TALK_TYPE_CHOICES.h_180)

    response = user_client.get(url)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/talk_voting/voting.html")
    assert talk.title in response.content.decode()
    assert training.title in response.content.decode()
    assert poster.title in response.content.decode()
    assert helpdesk.title in response.content.decode()


@mock.patch('conference.talk_voting.is_user_allowed_to_vote', return_value=True)
def test_talk_voting_vote_filters(mock_allowed_to_vote, user_client):
    get_default_conference()
    url = reverse("talk_voting:talks")
    # A talk for which the user hasn't voted
    not_voted = create_talk_for_user(user=None)
    # A talk for which the user has voted
    voted = create_talk_for_user(user=None)
    VotoTalk.objects.create(talk=voted, user=user_client.user, vote=VotingOptions.maybe)
    # A talk which the user submitted
    user_talk = create_talk_for_user(user=user_client.user)
    # A talk which the user did not submit, but he is a speaker
    speaker_talk = create_talk_for_user(user=None)
    TalkSpeakerFactory(talk=speaker_talk, speaker=user_client.user.speaker)

    response = user_client.get(url)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/talk_voting/voting.html")
    assert not_voted.title in response.content.decode()
    assert voted.title in response.content.decode()
    assert user_talk.title in response.content.decode()
    assert speaker_talk.title in response.content.decode()

    response = user_client.get(url, data={'filter': 'voted'})

    assert not_voted.title not in response.content.decode()
    assert voted.title in response.content.decode()
    assert user_talk.title not in response.content.decode()
    assert speaker_talk.title not in response.content.decode()

    response = user_client.get(url, data={'filter': 'not-voted'})

    assert not_voted.title in response.content.decode()
    assert voted.title not in response.content.decode()
    assert user_talk.title not in response.content.decode()
    assert speaker_talk.title not in response.content.decode()

    response = user_client.get(url, data={'filter': 'mine'})

    assert not_voted.title not in response.content.decode()
    assert voted.title not in response.content.decode()
    assert user_talk.title in response.content.decode()
    assert speaker_talk.title in response.content.decode()


@mock.patch('conference.talk_voting.is_user_allowed_to_vote', return_value=True)
def test_talk_voting_type_filters(mock_allowed_to_vote, user_client):
    get_default_conference()
    url = reverse("talk_voting:talks")
    talk = create_talk_for_user(user=None, type=TALK_TYPE_CHOICES.t_30)
    training = create_talk_for_user(user=None, type=TALK_TYPE_CHOICES.r_180)
    poster = create_talk_for_user(user=None, type=TALK_TYPE_CHOICES.i_60)
    helpdesk = create_talk_for_user(user=None, type=TALK_TYPE_CHOICES.h_180)

    response = user_client.get(url, data={'talk_type': 'talk'})

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/talk_voting/voting.html")
    assert talk.title in response.content.decode()
    assert training.title not in response.content.decode()
    assert poster.title not in response.content.decode()
    assert helpdesk.title not in response.content.decode()

    response = user_client.get(url, data={'talk_type': 'training'})

    assert talk.title not in response.content.decode()
    assert training.title in response.content.decode()
    assert poster.title not in response.content.decode()
    assert helpdesk.title not in response.content.decode()

    response = user_client.get(url, data={'talk_type': 'poster'})

    assert talk.title not in response.content.decode()
    assert training.title not in response.content.decode()
    assert poster.title in response.content.decode()
    assert helpdesk.title not in response.content.decode()

    response = user_client.get(url, data={'talk_type': 'helpdesk'})

    assert talk.title not in response.content.decode()
    assert training.title not in response.content.decode()
    assert poster.title not in response.content.decode()
    assert helpdesk.title in response.content.decode()


@mock.patch('conference.talk_voting.is_user_allowed_to_vote', return_value=True)
def test_talk_voting_both_filters(mock_allowed_to_vote, user_client):
    get_default_conference()
    url = reverse("talk_voting:talks")
    not_voted_talk = create_talk_for_user(user=None, type=TALK_TYPE_CHOICES.t_30)
    voted_training = create_talk_for_user(user=None, type=TALK_TYPE_CHOICES.r_180)
    VotoTalk.objects.create(talk=voted_training, user=user_client.user, vote=VotingOptions.maybe)

    response = user_client.get(url, data={'talk_type': 'talk', 'filter': 'voted'})

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/talk_voting/voting.html")
    assert not_voted_talk.title not in response.content.decode()
    assert voted_training.title not in response.content.decode()

    response = user_client.get(url, data={'talk_type': 'training', 'filter': 'voted'})

    assert not_voted_talk.title not in response.content.decode()
    assert voted_training.title in response.content.decode()

    response = user_client.get(url, data={'talk_type': 'talk', 'filter': 'not-voted'})

    assert not_voted_talk.title in response.content.decode()
    assert voted_training.title not in response.content.decode()


@mock.patch('conference.talk_voting.is_user_allowed_to_vote', return_value=True)
def test_talk_voting_hides_admin_talks(mock_allowed_to_vote, user_client):
    get_default_conference()
    url = reverse("talk_voting:talks")
    talk = create_talk_for_user(user=None, admin_type=TALK_ADMIN_TYPE[0][0])

    response = user_client.get(url)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/talk_voting/voting.html")
    assert talk.title not in response.content.decode()


@mock.patch('conference.talk_voting.is_user_allowed_to_vote', return_value=True)
def test_talk_voting_hides_accepted_talks(mock_allowed_to_vote, user_client):
    get_default_conference()
    url = reverse("talk_voting:talks")
    talk = create_talk_for_user(user=None, status=TALK_STATUS.accepted)

    response = user_client.get(url)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/talk_voting/voting.html")
    assert talk.title not in response.content.decode()


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
def test_view_talks_without_speaker_details_not_visible(mock_allowed_to_vote, user_client):
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.proposed, title="DeadBeef")
    talk2 = TalkFactory(status=TALK_STATUS.proposed, title="TestProposalForTests")
    speaker = SpeakerFactory(user=make_user())
    TalkSpeakerFactory(talk=talk2, speaker=speaker)

    url = reverse("talk_voting:talks")

    response = user_client.get(url)

    assert talk.title not in response.content.decode("utf8")
    assert talk2.title in response.content.decode("utf8")


def test_helper_query_talks_without_speaker_details_not_visible(db, user_client):
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.proposed, title="DeadBeef")
    talk2 = TalkFactory(status=TALK_STATUS.proposed, title="TestProposalForTests")
    speaker = SpeakerFactory(user=make_user())
    TalkSpeakerFactory(talk=talk2, speaker=speaker)

    talks = find_talks(user_client.user, Conference.objects.current(), [])
    assert talk not in talks

    assert talk2 in talks
