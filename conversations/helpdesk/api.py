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


def user_reply_to_thread(thread, content):
    # TODO(artcz) notification?
    with transaction.atomic():
        timestamp = timezone.now()

        msg = Message.objects.create(
            thread=thread,
            uuid=uuid.uuid4(),
            # NOTE(artcz) not sure if this is always safe assumption
            created_by=thread.created_by,
            is_staff_reply=True,
            content=content,
            created=timestamp,
            modified=timestamp,
        )

        thread.status = Thread.STATUS.USER_REPLIED
        thread.last_message_date = timestamp
        thread.save()

        # TODO: attachments?

    return msg
