
from django.contrib.admin.views.decorators import staff_member_required
from django.conf.urls import url
from django.template.response import TemplateResponse
from django import forms
from django.shortcuts import redirect

from conference.models import Conference
from conversations.models import Thread
from conversations.helpdesk.api import (
    staff_reply_to_thread,
    staff_add_internal_note,
)
from conversations.common_actions import (
    ThreadActions,
    ThreadFilters,
    get_actionable_threads,
    mark_thread_as_completed,
    reopen_thread,
)

# TODO: write a proper decorator here
helpdesk_staff_access = staff_member_required


@helpdesk_staff_access
def inbox(request):

    conference = Conference.objects.current()
    actionable = get_actionable_helpdesk_threads(conference)

    if ThreadFilters.order_by_last_message in request.GET:
        actionable = actionable.order_by('-last_message_date')

    if ThreadFilters.order_by_status in request.GET:
        actionable = actionable.order_by('status')

    return TemplateResponse(
        request, "ep19/conversations/helpdesk/inbox.html", {
            'ThreadFilters': ThreadFilters,
            'actionable': actionable,
        }
    )


@helpdesk_staff_access
def all_threads(request):

    conference = Conference.objects.current()
    all_threads = get_all_helpdesk_threads(conference)

    if ThreadFilters.order_by_last_message in request.GET:
        all_threads = all_threads.order_by('-last_message_date')

    if ThreadFilters.order_by_status in request.GET:
        all_threads = all_threads.order_by('status')

    return TemplateResponse(
        request, "ep19/conversations/helpdesk/all_threads.html", {
            'ThreadFilters': ThreadFilters,
            'all_threads': all_threads,
        }
    )


@helpdesk_staff_access
def thread(request, thread_uuid):

    thread = Thread.objects.get(uuid=thread_uuid)
    reply_form = ReplyForm()
    internal_note_form = InternalNoteForm()

    if request.method == 'POST':

        # TODO(artcz) Make a nicer solution here than nested ifs

        if ThreadActions.submit_internal_note in request.POST:
            internal_note_form = InternalNoteForm(
                data=request.POST, files=request.FILES
            )
            if internal_note_form.is_valid():
                staff_add_internal_note(
                    thread=thread,
                    added_by=request.user,
                    content=internal_note_form.cleaned_data['content']
                )
                return redirect('.')

        if ThreadActions.submit_reply_to_thread in request.POST:
            reply_form = ReplyForm(data=request.POST, files=request.FILES)

            if reply_form.is_valid():
                staff_reply_to_thread(
                    thread=thread,
                    replied_by=request.user,
                    content=reply_form.cleaned_data['content'],
                )
                return redirect('.')

        if ThreadActions.submit_thread_management in request.POST:
            if ThreadActions.complete_thread in request.POST:
                mark_thread_as_completed(thread, request.user)

            if ThreadActions.reopen_thread in request.POST:
                reopen_thread(thread, request.user)

            return redirect('.')

    return TemplateResponse(
        request, "ep19/conversations/helpdesk/thread.html", {
            'ThreadActions': ThreadActions,
            'thread': thread,
            'reply_form': reply_form,
            'internal_note_form': internal_note_form,
        }
    )


urlpatterns = [
    url(r"^inbox/$", inbox, name="inbox"),
    url(r"^all-threads/$", all_threads, name="all_threads"),

    url(
        r"^thread/(?P<thread_uuid>[\w-]+)/$",
        thread, name="thread",
    ),
]


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


class InternalNoteForm(forms.Form):
    content = forms.CharField()


class ReplyForm(forms.Form):
    content = forms.CharField(widget=forms.Textarea)
