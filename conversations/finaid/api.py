import uuid

from django.db import transaction
from django.utils import timezone

from conference.models import Conference
from common.jsonify import json_dumps

from conversations.models import Thread, Message
from conversations.common_actions import get_actionable_threads


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

    title = finaid_data['full_name']
    content = finaid_data.pop('supplements')
    metadata = json_dumps(finaid_data)

    with transaction.atomic():
        thread = Thread.objects.create(
            uuid=uuid.uuid4(),
            conference=conference,
            created_by=requested_by,
            title=title,
            status=Thread.STATUS.NEW,
            category=Thread.CATEGORIES.FINAID,
            last_message_date=timestamp,
            metadata=metadata,
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


def get_actionable_finaid_threads(conference):
    """
    Returns threads that require reply or further work/update from the staff.
    """
    return get_actionable_threads(conference).filter(
        category=Thread.CATEGORIES.FINAID,
    )


def get_all_finaid_threads(conference):
    return Thread.objects.filter(
        conference=conference,
        category=Thread.CATEGORIES.FINAID,
    ).order_by('status')
