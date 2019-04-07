
import uuid

from django.db import transaction
from django.utils import timezone
from django.template.response import TemplateResponse
from django.conf.urls import url

from conversations.models import Conference

from .models import Thread, Message
from .common_actions import get_actionable_threads


def get_actionable_helpdesk_threads(conference):
    """
    Returns threads that require reply or further work/update from the staff.
    """
    return get_actionable_threads(conference).filter(
        category=Thread.CATEGORIES.HELPDESK
    )


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

    return msg


def helpdesk_dashboard(request):

    conference = Conference.objects.current()
    actionable = get_actionable_helpdesk_threads(conference)

    return TemplateResponse(
        request, "ep19/bs/conversations/helpdesk/dashboard.html", {
            'actionable': actionable,
        }
    )


urlpatterns = [
    url(r'^$', helpdesk_dashboard, name="dashboard"),
]
