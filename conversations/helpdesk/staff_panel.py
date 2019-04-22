
from django.contrib.admin.views.decorators import staff_member_required
from django.conf.urls import url
from django.template.response import TemplateResponse

from conference.models import Conference
from conversations.helpdesk.api import (
    get_actionable_helpdesk_threads,
    get_all_helpdesk_threads,
)
from conversations.staff_interface import apply_ordering, staff_thread
from conversations.common_actions import ThreadFilters


# TODO: write a proper decorator here
helpdesk_staff_access = staff_member_required


@helpdesk_staff_access
def staff_helpdesk_inbox(request):

    conference = Conference.objects.current()
    actionable = get_actionable_helpdesk_threads(conference)
    actionable = apply_ordering(actionable, request)

    return TemplateResponse(
        request, "ep19/bs/conversations/helpdesk/inbox.html", {
            'ThreadFilters': ThreadFilters,
            'actionable': actionable,
        }
    )


@helpdesk_staff_access
def staff_helpdesk_all_threads(request):

    conference = Conference.objects.current()
    threads = get_all_helpdesk_threads(conference)
    threads = apply_ordering(threads, request)

    return TemplateResponse(
        request, "ep19/bs/conversations/helpdesk/all_threads.html", {
            'ThreadFilters': ThreadFilters,
            'all_threads': threads,
        }
    )


@helpdesk_staff_access
def staff_helpdesk_thread(request, thread_uuid):

    return staff_thread(
        request,
        thread_uuid,
        template_name='ep19/bs/conversations/helpdesk/thread.html'
    )


urlpatterns = [
    url(r"^inbox/$", staff_helpdesk_inbox, name="inbox"),
    url(r"^all-threads/$", staff_helpdesk_all_threads, name="all_threads"),
    url(
        r"^thread/(?P<thread_uuid>[\w-]+)/$",
        staff_helpdesk_thread,
        name="thread",
    ),
]
