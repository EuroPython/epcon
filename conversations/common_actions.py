
from django.db import transaction

from .models import Thread


class ConversationException(Exception):
    pass


class ConversationValidationError(ConversationException):
    pass


def notify(user, message):
    """
    Placeholder for notifications
    """
    pass


def mark_thread_as_completed(thread):
    if thread.status not in [
        Thread.STATUS.WAITING,
        Thread.STATUS.USER_REPLIED,
    ]:
        raise ConversationValidationError(
            # TODO(artcz) better error message
            f"Couldn't mark thread {thread.uuid} as completed "
            "because the status is not correct"
        )

    with transaction.atomic():
        thread.status = Thread.STATUS.COMPLETED
        thread.save()
        notify(
            thread.created_by, f"Thread {thread.uuid} was marked as completed"
        )


def reopen_thread(thread):
    thread.status = Thread.STATUS.REOPENED
    thread.save()


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
