import uuid

from django.db import transaction
from django.utils import timezone

from conference.models import Conference

from conversations.common_actions import get_actionable_threads
from conversations.models import Thread, Message


def create_new_support_request(conference, requested_by, title, content,
                               attachments=None):
    """
    Use this API instead of creating Threads and Messages directly
    """

    assert isinstance(conference, Conference)
    attachments = attachments or []

    timestamp = timezone.now()

    with transaction.atomic():
        thread = Thread.objects.create(
            uuid=uuid.uuid4(),
            conference=conference,
            created_by=requested_by,
            title=title,
            status=Thread.STATUS.NEW,
            category=Thread.CATEGORIES.HELPDESK,
            last_message_date=timestamp,
        )
        message = Message.objects.create(
            uuid=uuid.uuid4(),
            created_by=requested_by,
            thread=thread,
            content=content,
        )

        for attachment in attachments:
            attachment.message = message
            attachment.save()

    return thread, message


def get_actionable_helpdesk_threads(conference):
    """
    Returns threads that require reply or further work/update from the staff.
    """
    return get_actionable_threads(conference).filter(
        category=Thread.CATEGORIES.HELPDESK
    )


def get_all_helpdesk_threads(conference):
    return Thread.objects.filter(
        conference=conference,
        category=Thread.CATEGORIES.HELPDESK,
    ).order_by('status')
