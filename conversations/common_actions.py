import uuid

from django.db import transaction
from django.utils import timezone

from .models import Thread, Message


class ConversationException(Exception):
    pass


class ConversationValidationError(ConversationException):
    pass


def notify(user, message):
    """
    Placeholder for notifications
    """
    pass


def mark_thread_as_completed(thread, user):
    # if thread.status not in [
    #     Thread.STATUS.WAITING,
    #     Thread.STATUS.USER_REPLIED,
    # ]:
    #     raise ConversationValidationError(
    #         # TODO(artcz) better error message
    #         f"Couldn't mark thread {thread.uuid} as completed "
    #         "because the status is not correct"
    #     )

    with transaction.atomic():
        thread.status = Thread.STATUS.COMPLETED
        thread.save()

        Message.objects.create(
            uuid=uuid.uuid4(),
            created_by=user,
            thread=thread,
            content="Marked this thread as completed",
            is_public_note=True,
        )

        notify(
            thread.created_by, f"Thread {thread.uuid} was marked as completed"
        )


def reopen_thread(thread, user):
    with transaction.atomic():
        thread.status = Thread.STATUS.REOPENED
        thread.save()

        Message.objects.create(
            uuid=uuid.uuid4(),
            created_by=user,
            thread=thread,
            content="Reopened this thread",
            is_public_note=True,
        )


def get_actionable_threads(conference):
    """
    Returns threads that require reply or further work/update from the staff.
    """

    return Thread.objects.filter(
        conference=conference,
        status__in=[
            Thread.STATUS.NEW,
            Thread.STATUS.WAITING,
            Thread.STATUS.REOPENED,
            Thread.STATUS.USER_REPLIED,
        ]
    )


def get_stalled_threads(conference):
    """
    Returns threads that don't require reply or further work/update from the
    staff.
    """

    return Thread.objects.filter(
        conference=conference,
        status__in=[
            Thread.STATUS.STAFF_REPLIED,
            Thread.STATUS.COMPLETED,
        ]
    )


def user_reply_to_thread(thread, content):
    # TODO(artcz) notification?
    with transaction.atomic():
        timestamp = timezone.now()

        msg = Message.objects.create(
            thread=thread,
            uuid=uuid.uuid4(),
            # NOTE(artcz) not sure if this is always safe assumption
            created_by=thread.created_by,
            is_staff_reply=False,
            content=content,
            created=timestamp,
            modified=timestamp,
        )

        thread.status = Thread.STATUS.USER_REPLIED
        thread.last_message_date = timestamp
        thread.save()

        # TODO: attachments?

    return msg


class ThreadActions:
    # TODO: implement separat ThreadStaffActions and ThreadUserActions
    complete_thread = "complete_thread"
    reopen_thread = "reopen_thread"
    submit_reply_to_thread = "submit_reply_to_thread"
    submit_internal_note = "submit_internal_note"
    submit_thread_management = "submit_thread_management"
    change_priority = "change_priority"


class ThreadFilters:
    order_by_last_message = 'order_by_last_message'
    order_by_status = 'order_by_status'
    order_by_priority = 'order_by_priority'


def staff_reply_to_thread(thread, replied_by, content):
    # TODO(artcz) notification?
    with transaction.atomic():
        timestamp = timezone.now()

        msg = Message.objects.create(
            thread=thread,
            uuid=uuid.uuid4(),
            created_by=replied_by,
            is_staff_reply=True,
            content=content,
            created=timestamp,
            modified=timestamp,
        )

        thread.status = Thread.STATUS.STAFF_REPLIED
        thread.last_message_date = timestamp
        thread.save()

        # TODO: attachments(?)

    return msg


def staff_add_internal_note(thread, added_by, content):
    # TODO(artcz) notification?
    with transaction.atomic():
        timestamp = timezone.now()

        msg = Message.objects.create(
            thread=thread,
            uuid=uuid.uuid4(),
            created_by=added_by,
            is_internal_note=True,
            content=content,
            created=timestamp,
            modified=timestamp,
        )
        # Don't update the Thread.status, just save the message

        # TODO: attachments(?)

    return msg


def change_priority(thread, new_priority, changed_by):
    assert thread.priority != new_priority
    assert isinstance(new_priority, int)

    with transaction.atomic():
        old_priority = thread.priority
        thread.priority = new_priority

        priority_name = Thread.PRIORITIES[new_priority]
        if old_priority < thread.priority:
            content = f"Upgraded priority to {priority_name}"
        else:
            content = f"Downgraded priority to {priority_name}"

        msg = Message.objects.create(
            thread=thread,
            uuid=uuid.uuid4(),
            created_by=changed_by,
            is_internal_note=True,
            content=content
        )

        thread.save()

    return msg
