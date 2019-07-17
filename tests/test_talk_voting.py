from datetime import (
    date,
    timedelta,
)

import pytest
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone
from django_factory_boy import auth as auth_factories

from conference.models import Conference

from tests.common_tools import (
    redirects_to,
    template_used,
)
from tests.factories import (
    TicketFactory, AssopyUserFactory, SpeakerFactory,
    TalkFactory, TalkSpeakerFactory, P3TalkFactory,
)


class TestTalkVoting(TestCase):

    def setUp(self):
        self.conference = Conference.objects.create(
            code=settings.CONFERENCE_CONFERENCE,
            name=settings.CONFERENCE_CONFERENCE,
            # by default start with open CFP
            cfp_start=timezone.now() - timedelta(days=2),
            cfp_end=timezone.now()   + timedelta(days=2),
            voting_start=timezone.now() - timedelta(days=2),
            voting_end=timezone.now()   + timedelta(days=2)
        )
        self.user = auth_factories.UserFactory(
            email='joedoe@example.com', is_active=True)
        AssopyUserFactory(user=self.user)
        self.talk = TalkFactory()
        TalkSpeakerFactory(speaker=SpeakerFactory(user=self.user))
        P3TalkFactory(talk=self.talk)

    @pytest.mark.skip
    def test_access_to_talk_after_cfp(self):
        # TODO test access depending on voting settings
        self.client.login(email='joedoe@example.com', password='password123')
        response = self.client.get(self.talk.get_absolute_url())
        self.assertTemplateUsed(response, "conference/talk.html")

    def test_access_to_talk_xml(self):
        self.client.login(email='joedoe@example.com', password='password123')
        url = reverse("conference-talk-xml", args=[self.talk.slug])
        # works for non ajax
        response = self.client.get(url)
        assert response.status_code == 200
        self.assertTemplateUsed(response, "conference/talk.xml")
        assert response._headers['content-type'][1] == 'application/xml'

        # and for ajax
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert response.status_code == 200
        self.assertTemplateUsed(response, "conference/talk.xml")
        assert response._headers['content-type'][1] == 'application/xml'


def test_new_talk_voting_is_inaccessible_to_unauthenticated_users(db, client):
    url = reverse("talk_voting:talks")
    response = client.get(url)

    assert response.status_code == 302
    assert redirects_to(response, "/accounts/login/")


def test_new_talk_voting_is_unavailable_to_user_without_tickets(
    db, user_client
):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_NAME,
        voting_start=date.today() - timedelta(days=1),
        voting_end=date.today() + timedelta(days=1),
    )
    url = reverse("talk_voting:talks")

    response = user_client.get(url)
    assert response.status_code == 200
    assert template_used(
        response, "ep19/bs/talk_voting/voting_is_unavailable.html"
    )


def test_new_talk_voting_can_be_access_with_user_who_has_tickets(
    db, user_client
):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_NAME,
        voting_start=date.today() - timedelta(days=1),
        voting_end=date.today() + timedelta(days=1),
    )
    url = reverse("talk_voting:talks")
    TicketFactory(user=user_client.user)

    response = user_client.get(url)
    assert response.status_code == 200
    assert template_used(
        response, "ep19/bs/talk_voting/voting.html"
    )


@pytest.mark.xfail
def test_if_talk_voting_doesnt_contain_duplicates_if_there_are_more_speakers(
    db, user_client
):
    assert False
