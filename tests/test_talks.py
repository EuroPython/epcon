from datetime import timedelta

import pytest

from django.core.urlresolvers import reverse
from django.utils import timezone

from conference.models import TALK_STATUS, TALK_LEVEL
from conference.tests.factories.talk import TalkFactory
from conference.tests.factories.conference import ConferenceTagFactory
from tests.common_tools import setup_conference_with_typical_fares, redirects_to

pytestmark = [pytest.mark.django_db]


def test_talk_view_as_anonymous(client):
    # TODO: we only need the conference set up, we don't care about the fares;
    # another PR contains a helper that only sets up the conference
    setup_conference_with_typical_fares()
    talk = TalkFactory()
    url = reverse("talks:talk", args=[talk.slug])

    resp = client.get(url)

    assert resp.status_code == 200
    assert talk.title in resp.content.decode()
    assert talk.sub_title in resp.content.decode()
    assert talk.get_abstract() in resp.content.decode()
    assert "update talk" not in resp.content.decode().lower()


def test_talk_view_as_owner(user_client):
    tomorrow = timezone.now().date() + timedelta(days=1)
    setup_conference_with_typical_fares(end=tomorrow)
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.accepted)
    url = reverse("talks:talk", args=[talk.slug])

    resp = user_client.get(url)

    assert resp.status_code == 200
    assert talk.title in resp.content.decode()
    assert talk.sub_title in resp.content.decode()
    assert talk.get_abstract() in resp.content.decode()
    assert "update talk" in resp.content.decode().lower()


def test_cannot_update_talk_if_anonymous(client):
    setup_conference_with_typical_fares()
    talk = TalkFactory(status=TALK_STATUS.accepted)
    url = reverse("talks:update_talk", args=[talk.slug])

    resp = client.get(url)

    assert redirects_to(resp, reverse("accounts:login"))


def test_cannot_update_talk_if_not_owner(user_client):
    setup_conference_with_typical_fares()
    talk = TalkFactory(status=TALK_STATUS.accepted)
    url = reverse("talks:update_talk", args=[talk.slug])

    resp = user_client.get(url)

    assert resp.status_code == 403


def test_cannot_update_talk_if_talk_status_not_accepted(user_client):
    setup_conference_with_typical_fares()
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.proposed)
    url = reverse("talks:update_talk", args=[talk.slug])

    resp = user_client.get(url)

    assert resp.status_code == 403


def test_cannot_update_talk_if_conference_has_finished(user_client):
    yesterday = timezone.now().date() - timedelta(days=1)
    setup_conference_with_typical_fares(end=yesterday)
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.accepted)
    url = reverse("talks:update_talk", args=[talk.slug])

    resp = user_client.get(url)

    assert resp.status_code == 403


def test_update_talk_get(user_client):
    tomorrow = timezone.now().date() + timedelta(days=1)
    setup_conference_with_typical_fares(end=tomorrow)
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.accepted)
    url = reverse("talks:update_talk", args=[talk.slug])

    resp = user_client.get(url)

    assert resp.status_code == 200


def test_update_talk_post(user_client):
    tomorrow = timezone.now().date() + timedelta(days=1)
    setup_conference_with_typical_fares(end=tomorrow)
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.accepted)
    url = reverse("talks:update_talk", args=[talk.slug])

    tags = ConferenceTagFactory.create_batch(size=3)
    post_data = {
        "title": "new title",
        "sub_title": "new sub title",
        "abstract": "new abstract",
        "abstract_short": "new short abstract",
        "prerequisites": "new prerequisites",
        "level": TALK_LEVEL.advanced,
        "domain_level": TALK_LEVEL.advanced,
        "tags": ",".join(tag.name for tag in tags),
    }
    resp = user_client.post(url, data=post_data)

    talk.refresh_from_db()
    assert redirects_to(resp, talk.get_absolute_url())
    assert talk.title == post_data["title"]
    assert talk.sub_title == post_data["sub_title"]
    assert talk.get_abstract() == post_data["abstract"]
    assert talk.abstract_short == post_data["abstract_short"]
    assert talk.prerequisites == post_data["prerequisites"]
    assert talk.level == post_data["level"]
    assert talk.domain_level == post_data["domain_level"]
    assert set(talk.tags.all().values_list("pk", flat=True)) == set(
        [tag.pk for tag in tags]
    )
