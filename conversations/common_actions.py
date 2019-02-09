import uuid

from django.db import transaction

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


class ThreadActions:
    complete_thread = "complete_thread"
    reopen_thread = "reopen_thread"
    submit_reply_to_thread = "submit_reply_to_thread"
    submit_internal_note = "submit_internal_note"
    submit_thread_management = "submit_thread_management"


class ThreadFilters:
    order_by_last_message = 'order_by_last_message'
    order_by_status = 'order_by_status'
