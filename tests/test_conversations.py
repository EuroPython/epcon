"""
This module contains tests related to helpdesk, finaid, etc.
"""

from django.core.urlresolvers import reverse
from django.conf import settings

from conference.models import Conference
from conversations.models import Thread
from conversations.common_actions import ThreadActions
from conversations.user_interface import (
    FINAID_GRANT_CHOICES,
    FIRST_TIME_EUROPYTHON,
    SPEAKER_OR_COACH_CHOICES,
    VOLUNTEER_CHOICES,
)
from tests.common_tools import make_user, redirects_to, template_used


def _setup(client):
    Conference.objects.create(code=settings.CONFERENCE_CONFERENCE)
    make_user(email="joe@example.com", password="foobar")
    client.login(email="joe@example.com", password="foobar")


def _setup_admin(client):
    Conference.objects.create(code=settings.CONFERENCE_CONFERENCE)
    make_user(email="joe@example.com", password="foobar", is_staff=True)
    client.login(email="joe@example.com", password="foobar")


def test_user_panel_contains_a_link_to_user_threads(db, client):
    _setup(client)
    user_threads_url = reverse('user_conversations:threads')
    assert user_threads_url == '/conv/user/threads/'
    user_panel_url = reverse('user_panel:dashboard')
    assert user_panel_url == '/user-panel/'

    response = client.get(user_panel_url)

    assert user_threads_url in response.content.decode()


def test_user_panel_contains_link_to_finaid_request(db, client):
    _setup(client)
    new_finaid_url = reverse('user_conversations:new_finaid_request')
    assert new_finaid_url == '/conv/user/threads/start-new/finaid/'
    user_panel_url = reverse('user_panel:dashboard')
    assert user_panel_url == '/user-panel/'

    response = client.get(user_panel_url)

    assert new_finaid_url in response.content.decode()


def test_finaid_form_doesnt_work_for_users_that_are_not_logged_in(db, client):
    new_finaid_url = reverse('user_conversations:new_finaid_request')

    response = client.get(new_finaid_url)

    assert response.status_code == 302
    assert redirects_to(response, "/accounts/login/")


def test_finaid_form_works_for_logged_in_users(db, client):
    _setup(client)
    new_finaid_url = reverse("user_conversations:new_finaid_request")

    response = client.get(new_finaid_url)

    assert response.status_code == 200
    assert template_used(
        response,
        "ep19/bs/conversations/user_interface/new_finaid_request.html",
    )


def test_user_can_create_new_finaid_request(db, client):
    _setup(client)
    new_finaid_url = reverse("user_conversations:new_finaid_request")

    response = client.post(new_finaid_url, {
        "full_name": "Joe Doe",
        "type_of_grant": [FINAID_GRANT_CHOICES.TICKET,
                          FINAID_GRANT_CHOICES.TRAVEL],
        "travel_amount": 123,
        "accommodation_amount": 0,
        "profession": "IT",
        "affiliation": "EPS",
        "country_of_residence": "Poland",
        "date_of_birth": "2000-01-01",
        "gender": "Prefer not to disclose",
        "motivation": "because it's great",
        "involvement": "github.com/europython/epcon",
        "expectations": "Learn more and network",
        "portfolio": "github.com/europython",
        "how_do_you_use_python": "automation",
        "first_time_europython": FIRST_TIME_EUROPYTHON.YES,
        "speaker_or_coach": SPEAKER_OR_COACH_CHOICES.YES,
        "did_you_volunteer": VOLUNTEER_CHOICES.YES,
        "supplements": "My keyboard doesn't do `n` very well :("
    })

    assert response.status_code == 302
    thread = Thread.objects.get()  # implies there's only one
    assert thread.category == Thread.CATEGORIES.FINAID
    assert redirects_to(response, thread.get_user_url())


def test_user_panel_doesnt_contain_link_to_helpdesk_inbox_if_user_is_not_staff(
    db, client
):
    ...


def test_user_panel_contains_link_to_helpdesk_inbox_if_user_is_staff(
    db, client
):
    ...


def test_user_panel_contains_link_to_finaid_inbox_if_user_is_staff(db, client):
    ...


def test_user_panel_doesnt_cotain_link_to_finaid_inbox_if_user_is_not_staff(
    db, client
):
    ...


def test_user_threads_are_not_accessible_to_unauthorised_url(db, client):
    user_threads_url = reverse('user_conversations:threads')
    response = client.get(user_threads_url)

    assert response.status_code == 302
    assert redirects_to(response, '/accounts/login/')


def test_user_threads_is_empty_if_there_are_no_threads(db, client):
    Conference.objects.create(code=settings.CONFERENCE_CONFERENCE)
    make_user(email="joe@example.com", password="foobar")
    client.login(email="joe@example.com", password="foobar")
    user_threads_url = reverse("user_conversations:threads")

    response = client.get(user_threads_url)
    assert template_used(
        response, "ep19/bs/conversations/user_interface/threads.html"
    )

    assert "Yay, no questions so far" in response.content.decode()


def test_user_threads_contains_link_to_creating_new_thread(db, client):
    Conference.objects.create(code=settings.CONFERENCE_CONFERENCE)
    make_user(email="joe@example.com", password="foobar")
    client.login(email="joe@example.com", password="foobar")
    user_threads_url = reverse("user_conversations:threads")
    new_thread_url = reverse("user_conversations:start_new_thread")
    assert new_thread_url == '/conv/user/threads/start-new/'

    response = client.get(user_threads_url)
    assert template_used(
        response, "ep19/bs/conversations/user_interface/threads.html"
    )

    assert "Start new thread" in response.content.decode()
    assert new_thread_url in response.content.decode()


def test_new_thread_renders_correct_template(db, client):
    _setup(client)

    user_new_thread_url = reverse("user_conversations:start_new_thread")
    assert user_new_thread_url == "/conv/user/threads/start-new/"

    response = client.get(user_new_thread_url)
    assert template_used(
        response, "ep19/bs/conversations/user_interface/start_new_thread.html"
    )


def test_post_to_new_thread_creates_new_threads_and_redirects(db, client):
    _setup(client)
    user_new_thread_url = reverse("user_conversations:start_new_thread")
    assert Thread.objects.all().count() == 0

    response = client.post(user_new_thread_url, {
        'title': "This is a title",
        'content': "This is some content",
    })

    assert response.status_code == 302
    thread = Thread.objects.get()  # implies there's only one
    assert thread.category == Thread.CATEGORIES.HELPDESK
    assert redirects_to(response, thread.get_user_url())
    assert thread.get_user_url() == f'/conv/user/thread/{thread.uuid}/'
    assert thread.status == Thread.STATUS.NEW


def test_user_can_post_to_thread_and_this_changes_status_of_thread(db, client):
    """
    NOTE: This test's setup should be improved with ThreadFactory instead
    """
    # ==== Copy of previous test as setup
    _setup(client)
    user_new_thread_url = reverse("user_conversations:start_new_thread")
    assert Thread.objects.all().count() == 0

    response = client.post(user_new_thread_url, {
        'title': "This is a title",
        'content': "This is some content",
    })
    thread = Thread.objects.get()  # implies there's only one
    assert response.status_code == 302
    assert redirects_to(response, thread.get_user_url())
    assert thread.get_user_url() == f'/conv/user/thread/{thread.uuid}/'
    assert thread.status == Thread.STATUS.NEW

    # ==============
    response = client.post(thread.get_user_url(), {
        ThreadActions.submit_reply_to_thread: True,
        "content": "This is my reply",
    })

    thread.refresh_from_db()
    assert thread.status == Thread.STATUS.USER_REPLIED


def test_staff_can_reply_to_thread_and_this_changes_status_of_thread(
    db, client
):
    ...


def test_staff_helpdesk_inbox_is_not_accessible_if_user_is_not_staff(
    db, client
):
    _setup_admin(client)
    ...


def test_staff_helpdesk_inbox_contains_no_elements_if_there_are_no_threads(
    db, client
):
    _setup_admin(client)
    staff_helpdesk_inbox_url = reverse("staff_helpdesk:inbox")

    response = client.get(staff_helpdesk_inbox_url)
    assert response.status_code == 200
    assert template_used(response, "ep19/bs/conversations/helpdesk/inbox.html")
