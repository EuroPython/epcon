# coding: utf-8

from datetime import timedelta

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone

from django_factory_boy import auth as auth_factories

from assopy.tests.factories.user import UserFactory as AssopyUserFactory
from conference.tests.factories.talk import TalkFactory, TalkSpeakerFactory
from conference.tests.factories.speaker import SpeakerFactory
from conference.models import Conference
from p3.tests.factories.talk import P3TalkFactory


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
