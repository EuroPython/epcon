
from django.contrib.admin.views.decorators import staff_member_required
from django.conf.urls import url
from django.template.response import TemplateResponse

from conference.models import Conference
from conversations.finaid.api import (
    get_actionable_finaid_threads,
    get_all_finaid_threads,
)
from conversations.staff_interface import staff_thread, apply_ordering
from conversations.common_actions import ThreadFilters

# TODO: write a proper decorator here
finaid_staff_access = staff_member_required


@finaid_staff_access
def staff_finaid_inbox(request):

    conference = Conference.objects.current()
    actionable = get_actionable_finaid_threads(conference)
    actionable = apply_ordering(actionable, request)

    return TemplateResponse(
        request, "ep19/bs/conversations/finaid/inbox.html", {
            'ThreadFilters': ThreadFilters,
            'actionable': actionable,
        }
    )


@finaid_staff_access
def staff_finaid_threads(request):

    conference = Conference.objects.current()
    threads = get_all_finaid_threads(conference)
    threads = apply_ordering(threads, request)

    return TemplateResponse(
        request, "ep19/bs/conversations/finaid/all_threads.html", {
            'ThreadFilters': ThreadFilters,
            'all_threads': threads,
        }
    )


@finaid_staff_access
def staff_finaid_single_thread(request, thread_uuid):

    return staff_thread(
        request,
        thread_uuid,
        template_name='ep19/bs/conversations/finaid/thread.html'
    )


urlpatterns = [
    url(r"^inbox/$", staff_finaid_inbox, name="inbox"),
    url(r"^all-requests/$", staff_finaid_threads, name="all_finaid_threads"),
    url(
        r"^request/(?P<thread_uuid>[\w-]+)/$",
        staff_finaid_single_thread,
        name="single_thread",
    ),
]
