
from django.conf import settings

from pytest import mark

# from conversations.models import Message
from conference.models import Conference
from conversations.common_actions import (
    mark_thread_as_completed,
    staff_reply_to_thread,
    user_reply_to_thread,
)
from conversations.helpdesk.api import (
    get_actionable_helpdesk_threads,
    create_new_support_request,
)
from conversations.models import Thread

from .common_tools import sequence_equals, make_user


def make_conference():
    return Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
    )


@mark.django_db
def test_if_filtering_actionable_messages_is_empty_if_there_are_no_messages():
    conference = make_conference()

    assert sequence_equals(get_actionable_helpdesk_threads(conference), [])


@mark.django_db
def test_new_thread_is_actionable():
    conference = make_conference()
    user = make_user()

    thread, message = create_new_support_request(
        conference,
        requested_by=user,
        title="Some Request",
        content="Whatever content",
    )
    assert thread.status == Thread.STATUS.NEW

    assert sequence_equals(
        get_actionable_helpdesk_threads(conference),
        [thread]
    )


@mark.django_db
def test_new_thread_all_new_threads_are_actionable():
    conference = make_conference()
    user = make_user()

    for i in range(10):
        create_new_support_request(
            conference,
            requested_by=user,
            title="Some Request",
            content="Whatever content",
        )

    assert len(get_actionable_helpdesk_threads(conference)) == 10


@mark.django_db
def test_closed_threads_are_not_actionable():
    conference = make_conference()
    user = make_user()
    staff_member = make_user(is_staff=True)

    thread1, msg1 = create_new_support_request(
        conference,
        requested_by=user,
        title="Some Request",
        content="Whatever content",
    )

    thread2, msg2 = create_new_support_request(
        conference,
        requested_by=user,
        title="Some Request",
        content="Whatever content",
    )

    assert sequence_equals(
        get_actionable_helpdesk_threads(conference), [thread2, thread1]
    )

    staff_reply_to_thread(
        thread2, replied_by=staff_member, content="This is staff reply"
    )

    assert sequence_equals(
        get_actionable_helpdesk_threads(conference), [thread1]
    )


@mark.django_db
def test_replied_thread_is_actionable_again():
    conference = make_conference()
    user = make_user()
    staff_member = make_user(is_staff=True)

    thread, msg = create_new_support_request(
        conference,
        requested_by=user,
        title="Some Request",
        content="Whatever content",
    )

    staff_reply_to_thread(
        thread, replied_by=staff_member, content="This is staff reply"
    )

    assert sequence_equals(get_actionable_helpdesk_threads(conference), [])

    user_reply_to_thread(thread, content="This is some content")

    assert sequence_equals(
        get_actionable_helpdesk_threads(conference),
        [thread]
    )


@mark.django_db
def test_completed_threads_are_not_actionable():
    conference = make_conference()
    user = make_user()
    staff_member = make_user(is_staff=True)

    thread, msg = create_new_support_request(
        conference,
        requested_by=user,
        title="Some Request",
        content="Whatever content",
    )

    staff_reply_to_thread(
        thread, replied_by=staff_member, content="This is staff reply"
    )

    assert sequence_equals(get_actionable_helpdesk_threads(conference), [])

    user_reply_to_thread(thread, content="This is some content")

    assert sequence_equals(
        get_actionable_helpdesk_threads(conference),
        [thread]
    )

    mark_thread_as_completed(thread, user)

    assert sequence_equals(get_actionable_helpdesk_threads(conference), [])
