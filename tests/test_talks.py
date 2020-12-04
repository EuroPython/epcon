from datetime import timedelta

import pytest

from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from conference.models import TALK_STATUS, TALK_LEVEL
from tests.factories import (
    EventFactory,
    UserFactory,
    TalkFactory,
    ConferenceTagFactory,
    TalkSpeakerFactory,
)
from tests.common_tools import get_default_conference, redirects_to, template_used, make_user

pytestmark = [pytest.mark.django_db]


def test_talk_view_as_anonymous(client):
    original_abstract = "Hello!\nGoto http://example.com"
    # newlines should become BR, urls should be linked
    expected_abstract = ('Hello!<br>Goto <a href="http://example.com" rel="nofollow">'
                         'http://example.com</a>')
    get_default_conference()
    talk = TalkFactory()
    talk.setAbstract(original_abstract)
    url = reverse("talks:talk", args=[talk.slug])

    resp = client.get(url)

    assert resp.status_code == 200
    assert talk.title in resp.content.decode()
    assert talk.sub_title in resp.content.decode()
    assert expected_abstract in resp.content.decode()
    assert "update talk" not in resp.content.decode().lower()


def test_talk_view_as_owner(user_client):
    tomorrow = timezone.now().date() + timedelta(days=1)
    get_default_conference(conference_end=tomorrow)
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.accepted)
    url = reverse("talks:talk", args=[talk.slug])

    resp = user_client.get(url)

    assert resp.status_code == 200
    assert talk.title in resp.content.decode()
    assert talk.sub_title in resp.content.decode()
    assert talk.get_abstract() in resp.content.decode()
    assert "update talk" in resp.content.decode().lower()


def test_cannot_update_talk_if_anonymous(client):
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.accepted)
    url = reverse("talks:update_talk", args=[talk.slug])

    resp = client.get(url)

    assert redirects_to(resp, reverse("accounts:login"))


def test_cannot_update_talk_if_not_owner(user_client):
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.accepted)
    url = reverse("talks:update_talk", args=[talk.slug])

    resp = user_client.get(url)

    assert resp.status_code == 403


def test_cannot_update_talk_if_talk_status_not_accepted(user_client):
    get_default_conference()
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.proposed)
    url = reverse("talks:update_talk", args=[talk.slug])

    resp = user_client.get(url)

    assert resp.status_code == 403


def test_can_update_if_is_speaker_but_not_owner(user_client):
    get_default_conference()
    talk = TalkFactory(created_by=make_user(), status=TALK_STATUS.accepted)
    # Make the user a Speaker at the Talk
    TalkSpeakerFactory(talk=talk, speaker__user=user_client.user)
    url = reverse("talks:update_talk", args=[talk.slug])

    resp = user_client.get(url)

    assert resp.status_code == 200


def test_cannot_update_talk_if_conference_has_finished(user_client):
    yesterday = timezone.now().date() - timedelta(days=1)
    get_default_conference(conference_end=yesterday)
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.accepted)
    url = reverse("talks:update_talk", args=[talk.slug])

    resp = user_client.get(url)

    assert resp.status_code == 403


def test_update_talk_get(user_client):
    tomorrow = timezone.now().date() + timedelta(days=1)
    get_default_conference(conference_end=tomorrow)
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.accepted)
    url = reverse("talks:update_talk", args=[talk.slug])

    resp = user_client.get(url)

    assert resp.status_code == 200


def test_update_talk_post(user_client):
    tomorrow = timezone.now().date() + timedelta(days=1)
    get_default_conference(conference_end=tomorrow)
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


def test_anonymous_cannot_get_submit_slides(client):
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.accepted)

    url = reverse("talks:submit_slides", args=[talk.slug])
    response = client.get(url)

    assert redirects_to(response, reverse('accounts:login'))


def test_not_author_cannot_get_submit_slides(user_client):
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.accepted)

    url = reverse("talks:submit_slides", args=[talk.slug])
    response = user_client.get(url)

    assert response.status_code == 403


def test_author_can_get_submit_slides(user_client):
    get_default_conference()
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.accepted)

    url = reverse("talks:submit_slides", args=[talk.slug])
    response = user_client.get(url)

    assert response.status_code == 200
    assert template_used(response, "conference/talks/update_talk.html")


def test_author_can_post_submit_slides(user_client):
    get_default_conference()
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.accepted)
    assert not talk.slides

    url = reverse("talks:submit_slides", args=[talk.slug])
    payload = {"slides": SimpleUploadedFile('slides.pdf', 'pdf content'.encode())}
    response = user_client.post(url, data=payload)

    assert redirects_to(response, talk.get_absolute_url())
    talk.refresh_from_db()
    assert talk.slides

def test_author_can_post_submit_slides_url(user_client):
    get_default_conference()
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.accepted)

    url = reverse("talks:submit_slides", args=[talk.slug])
    payload = {"slides_url": "https://epstage.europython.eu"}
    response = user_client.post(url, data=payload)

    assert redirects_to(response, talk.get_absolute_url())
    talk.refresh_from_db()
    assert talk.slides_url


def test_author_can_post_submit_repository_url(user_client):
    get_default_conference()
    talk = TalkFactory(created_by=user_client.user, status=TALK_STATUS.accepted)

    url = reverse("talks:submit_slides", args=[talk.slug])
    payload = {"repository_url": "https://epstage.europython.eu"}
    response = user_client.post(url, data=payload)

    assert redirects_to(response, talk.get_absolute_url())
    talk.refresh_from_db()
    assert talk.repository_url


def test_submit_slides_url_on_talk_detail_page(client):
    """
    The submit slides button only appears if the user is the author of the talk.
    """
    get_default_conference()
    talk = TalkFactory(created_by=UserFactory(), status=TALK_STATUS.accepted)
    url = talk.get_absolute_url()
    submit_slides_url = reverse("talks:submit_slides", args=[talk.slug])

    # URL does not appear for anonymous users
    response = client.get(url)

    assert 'submit slides' not in response.content.decode().lower()
    assert submit_slides_url not in response.content.decode()

    # URL does not appear for authenticated users
    client.force_login(UserFactory())
    response = client.get(url)

    assert 'submit slides' not in response.content.decode().lower()
    assert submit_slides_url not in response.content.decode()

    # URL does appear for the talk owner
    client.force_login(talk.created_by)
    response = client.get(url)

    assert 'submit slides' in response.content.decode().lower()
    assert submit_slides_url in response.content.decode()


def test_view_slides_url_on_talk_detail_page(client):
    """
    The download slides button only appears if the slides have been uploaded.
    """
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.accepted)
    url = talk.get_absolute_url()

    # Slides URL does not appear when the slides haven't been uploaded
    response = client.get(url)

    assert not talk.slides
    assert 'download/view slides' not in response.content.decode().lower()

    # Slides URL does appear when the slides have been uploaded
    talk.slides = SimpleUploadedFile('slides.pdf', 'pdf content'.encode())
    talk.save()

    response = client.get(url)

    assert 'download/view slides' in response.content.decode().lower()


def test_talk_for_other_than_current_conference(client):
    """
    Only display talks for the current conference.
    """
    get_default_conference()
    other_conference = get_default_conference(code='ep_other')
    talk_in_other_conference = TalkFactory(conference=other_conference.code)

    url = reverse("talks:talk", args=[talk_in_other_conference.slug])
    resp = client.get(url)

    assert resp.status_code == 404


def test_show_talk_link_in_schedule(client):
    """
    The talk url points to the schedule, with correct talk slug, and time in utc
    """
    get_default_conference()
    talk = TalkFactory(status=TALK_STATUS.accepted)
    event = EventFactory(talk=talk)
    url = talk.get_absolute_url()

    response = client.get(url)

    start_time = event.start_time.strftime('%H:%M-UTC')
    assert f"{talk.slug}#{start_time}" in response.content.decode()
