
from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse
from django.http import Http404
from django.shortcuts import redirect
from django import forms

from conference.models import Conference
from conversations.models import Thread
from conversations.common_actions import (
    ThreadFilters,
    ThreadActions,
    user_reply_to_thread,
)


@login_required
def threads(request):

    threads = Thread.objects.filter(
        conference=Conference.objects.current(),
        created_by=request.user
    ).order_by('-last_message_date')

    return TemplateResponse(
        request, "ep19/conversations/user_interface/threads.html", {
            "threads": threads,
            "ThreadFilters": ThreadFilters,
        }
    )


@login_required
def start_new_thread(request):
    return TemplateResponse(
        request, "ep19/conversations/user_interface/start_new_thread.html", {
        }
    )


@login_required
def user_thread(request, thread_uuid):
    thread = Thread.objects.get(uuid=thread_uuid)

    if thread.created_by != request.user:
        raise Http404()

    user_reply_form = UserReplyForm()

    if request.method == "POST":
        if ThreadActions.submit_reply_to_thread in request.POST:
            user_reply_form = UserReplyForm(
                data=request.POST, files=request.FILES
            )
            if user_reply_form.is_valid():
                user_reply_to_thread(
                    thread=thread,
                    # replied_by=request.user,
                    content=user_reply_form.cleaned_data["content"],
                )
                return redirect(".")

    return TemplateResponse(
        request,
        "ep19/conversations/user_interface/thread.html",
        {
            "thread": thread,
            "ThreadActions": ThreadActions,
            "user_reply_form": user_reply_form,
        },
    )


urlpatterns = [
    url(r"^threads/$", threads, name="threads"),
    url(r"^threads/start-new/$", start_new_thread, name="start_new_thread"),
    url(
        r"^thread/(?P<thread_uuid>[\w-]+)/$",
        user_thread, name="user_thread",
    ),
]


class UserReplyForm(forms.Form):
    content = forms.CharField(widget=forms.Textarea)
