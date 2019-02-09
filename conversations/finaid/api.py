import uuid

from django.db import transaction
from django.utils import timezone

from conference.models import Conference
from common.jsonify import json_dumps

from conversations.models import Thread, Message


def create_new_finaid_request(
    conference,
    requested_by,
    finaid_data,
    attachments=None,
):
    """
    Use this API instead of creating Threads and Messages directly
    """

    assert isinstance(conference, Conference)
    attachments = attachments or []

    timestamp = timezone.now()

    title = 'Finaid request -- %s' % finaid_data['full_name']
    content = json_dumps(finaid_data)

    with transaction.atomic():
        thread = Thread.objects.create(
            uuid=uuid.uuid4(),
            conference=conference,
            created_by=requested_by,
            title=title,
            status=Thread.STATUS.NEW,
            category=Thread.CATEGORIES.FINAID,
            last_message_date=timestamp,
        )
        message = Message.objects.create(
            uuid=uuid.uuid4(),
            created_by=requested_by,
            thread=thread,
            content=content,
        )

        # TODO: maybe FinaidRequest object as well, to allow for easier
        # aggreagation of the results?

        for attachment in attachments:
            attachment.message = message
            attachment.save()

    return thread, message
