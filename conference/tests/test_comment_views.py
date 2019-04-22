import time

from pytest import mark

from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType

from conference.tests.factories.conference import ConferenceFactory
from conference.tests.factories.talk import TalkFactory, CommentFactory
from p3.tests.factories.talk import P3TalkFactory
from tests.common_tools import make_user, redirects_to


@mark.django_db
def test_view_comments_anonymous(client):
    conference = ConferenceFactory()
    talk = TalkFactory(status="accepted", conference=conference.code)
    P3TalkFactory(talk=talk)

    resp = client.get(talk.get_absolute_url())

    # No comments for the talk, so the comment list is not displayed.
    assert 'id="comments"' not in resp.content.decode()
    # Anonymous user should not be able to post comments.
    assert 'id="add-comment"' not in resp.content.decode()

    CommentFactory(content_object=talk)

    resp = client.get(talk.get_absolute_url())

    # A comment exists for the talk, so the comment list is visible.
    assert 'id="comments"' in resp.content.decode()


@mark.django_db
def test_add_comments_anonymous(client):
    conference = ConferenceFactory()
    talk = TalkFactory(status="accepted", conference=conference.code)
    talk_content_type = ContentType.objects.get_for_model(talk)

    resp = client.post(
        reverse("hcomments-post-comment"),
        data={
            "comment": "some comment",
            "content_type": "{}.{}".format(
                talk_content_type.app_label, talk_content_type.model
            ),
            "object_pk": talk.pk,
            "timestamp": time.time(),
        },
    )

    assert redirects_to(resp, reverse("accounts:login"))


@mark.django_db
def test_view_comment_authenticated(client):
    make_user()
    conference = ConferenceFactory()
    talk = TalkFactory(status="accepted", conference=conference.code)
    P3TalkFactory(talk=talk)
    CommentFactory(content_object=talk)

    assert client.login(email="joedoe@example.com", password="password123")
    resp = client.get(talk.get_absolute_url())

    # A comment exsists for the talk, so the comment list is visible.
    assert 'id="comments"' in resp.content.decode()
    # Authenticated user should be able to post comments.
    assert 'id="add-comment"' in resp.content.decode()


@mark.django_db
def test_add_comments_authenticated(client, mocker):
    mocker.patch("django_comments.forms.CommentForm.clean_security_hash")

    make_user()
    conference = ConferenceFactory()
    talk = TalkFactory(status="accepted", conference=conference.code)
    talk_content_type = ContentType.objects.get_for_model(talk)
    comment_body = "some comment"

    assert client.login(email="joedoe@example.com", password="password123")
    resp = client.post(
        reverse("hcomments-post-comment"),
        data={
            "comment": comment_body,
            "content_type": "{}.{}".format(
                talk_content_type.app_label, talk_content_type.model
            ),
            "object_pk": talk.pk,
            "timestamp": int(time.time()),
            "security_hash": "a" * 40,  # Min length of the hash
        },
    )

    assert resp.status_code == 200
    assert 'id="comment-1"' in resp.content.decode()
    assert comment_body in resp.content.decode()
