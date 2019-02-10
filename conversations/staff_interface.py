
from django.shortcuts import redirect
from django import forms
from django.template.response import TemplateResponse

from conversations.models import Thread
from conversations.common_actions import (
    ThreadActions,
    ThreadFilters,
    mark_thread_as_completed,
    reopen_thread,
    staff_reply_to_thread,
    staff_add_internal_note,
    change_priority,
)


def staff_thread(
    request,
    thread_uuid,
    template_name="ep19/conversations/helpdesk/thread.html"
):

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

        if ThreadActions.change_priority in request.POST:
            new_priority = int(request.POST['priority'])
            change_priority(thread, new_priority, request.user)

            return redirect('.')

    return TemplateResponse(
        request, template_name, {
            'ThreadActions': ThreadActions,
            'thread': thread,
            'reply_form': reply_form,
            'internal_note_form': internal_note_form,
            'change_priority_form': ChangePriorityForm(instance=thread),
        }
    )


class InternalNoteForm(forms.Form):
    content = forms.CharField()


class ReplyForm(forms.Form):
    content = forms.CharField(widget=forms.Textarea)


class ChangePriorityForm(forms.ModelForm):

    class Meta:
        model = Thread
        fields = ['priority']


def apply_ordering(threads, request):

    if ThreadFilters.order_by_last_message in request.GET:
        threads = threads.order_by('-last_message_date')

    if ThreadFilters.order_by_status in request.GET:
        threads = threads.order_by('status')

    if ThreadFilters.order_by_priority in request.GET:
        threads = threads.order_by('priority')

    return threads
