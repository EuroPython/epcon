import uuid

from django.db import transaction
from django.utils import timezone

from conference.models import Conference

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
