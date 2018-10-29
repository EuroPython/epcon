# coding: utf-8
from pytest import mark

from conference.tests.factories.conference import ConferenceFactory
from conference.tests.factories.talk import TalkFactory, CommentFactory
from p3.tests.factories.talk import P3TalkFactory
from tests.common_tools import make_user


@mark.django_db
def test_add_comment_anonymous(client):
    conference = ConferenceFactory()
    talk = TalkFactory(status='accepted', conference=conference.code)
    P3TalkFactory(talk=talk)

    resp = client.get(talk.get_absolute_url())

    # No comments for the talk, so the comment list is not displayed.
    assert 'id="comments"' not in resp.content
    # Anonymous user should not be able to post comments.
    assert 'id="add-comment"' not in resp.content

    CommentFactory(content_object=talk)

    resp = client.get(talk.get_absolute_url())

    # A comment exists for the talk, so the comment list is visible.
    assert 'id="comments"' in resp.content


@mark.django_db
def test_add_comment_authenticated(client):
    make_user()
    conference = ConferenceFactory()
    talk = TalkFactory(status='accepted', conference=conference.code)
    P3TalkFactory(talk=talk)
    CommentFactory(content_object=talk)

    assert client.login(email='joedoe@example.com', password='password123')
    resp = client.get(talk.get_absolute_url())

    # A comment exsists for the talk, so the comment list is visible.
    assert 'id="comments"' in resp.content
    # Authenticated user should be able to post comments.
    assert 'id="add-comment"' in resp.content
