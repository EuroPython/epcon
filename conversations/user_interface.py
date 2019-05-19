from django import forms
from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from model_utils import Choices

from conference.models import Conference
from conversations.common_actions import (
    ThreadActions,
    ThreadFilters,
    mark_thread_as_completed,
    reopen_thread,
    user_reply_to_thread,
)
from conversations.finaid.api import create_new_finaid_request
from conversations.helpdesk.api import create_new_support_request
from conversations.models import Thread


@login_required
def threads(request):

    threads = Thread.objects.filter(
        conference=Conference.objects.current(), created_by=request.user
    ).order_by("-last_message_date")

    return TemplateResponse(
        request,
        "ep19/bs/conversations/user_interface/threads.html",
        {"threads": threads, "ThreadFilters": ThreadFilters},
    )


@login_required
def start_new_thread(request):

    form = UserCreateHelpdeskRequestForm()

    if request.method == "POST":
        form = UserCreateHelpdeskRequestForm(
            data=request.POST, files=request.FILES
        )

        if form.is_valid():
            thread, _ = create_new_support_request(
                conference=Conference.objects.current(),
                requested_by=request.user,
                title=form.cleaned_data["title"],
                content=form.cleaned_data["content"],
                # TODO: attachments
            )
            # TODO: messages.succeess
            return redirect(thread.get_user_url())

    return TemplateResponse(
        request,
        "ep19/bs/conversations/user_interface/start_new_thread.html",
        {"new_support_request_form": form},
    )


@login_required
def new_finaid_request(request):

    form = UserNewFinaidRequest()

    if request.method == "POST":
        form = UserNewFinaidRequest(data=request.POST, files=request.FILES)

        if form.is_valid():
            thread, _ = create_new_finaid_request(
                conference=Conference.objects.current(),
                requested_by=request.user,
                finaid_data=dict(**form.cleaned_data),
            )
            return redirect(thread.get_user_url())

    return TemplateResponse(
        request,
        "ep19/bs/conversations/user_interface/new_finaid_request.html",
        {"new_finaid_request_form": form},
    )


@login_required
def user_thread(request, thread_uuid):
    thread = Thread.objects.get(uuid=thread_uuid)

    if thread.created_by != request.user:
        raise Http404()

    user_reply_form = UserReplyForm()

    if request.method == "POST":

        if ThreadActions.submit_thread_management in request.POST:
            if ThreadActions.complete_thread in request.POST:
                mark_thread_as_completed(thread, request.user)

            if ThreadActions.reopen_thread in request.POST:
                reopen_thread(thread, request.user)

            return redirect('.')

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
        "ep19/bs/conversations/user_interface/thread.html",
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
        r"^threads/start-new/finaid/$",
        new_finaid_request,
        name="new_finaid_request",
    ),
    url(r"^thread/(?P<thread_uuid>[\w-]+)/$", user_thread, name="user_thread"),
]


class UserReplyForm(forms.Form):
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))


class UserCreateHelpdeskRequestForm(forms.Form):
    title = forms.CharField()
    content = forms.CharField(widget=forms.Textarea)


class UserNewFinaidRequest(forms.Form):

    FINAID_GRANT_CHOICES = Choices(
        ("TICKET", "Ticket"),
        ("TRAVEL_AND_ACCOMODATION", "Travel and/or Accommodation"),
    )

    full_name = forms.CharField(label="Full name")

    type_of_grant = forms.MultipleChoiceField(
        choices=FINAID_GRANT_CHOICES, widget=forms.CheckboxSelectMultiple
    )

    # TODO: add conditional validation here
    travel_amount = forms.IntegerField(
        help_text="Approx. amount in EUR, note it should not exceed 300EUR",
        required=False,
    )

    accomodation_amount = forms.IntegerField(
        help_text="Approx. amount in EUR, note it should not exceed 300EUR",
        required=False,
    )

    profession = forms.CharField()
    affiliation = forms.CharField()
    country_of_residence = forms.CharField()
    date_of_birth = forms.DateField(help_text="Format YYYY-MM-DD")
    gender = forms.CharField()
    motivation = forms.CharField(
        help_text="Why do you want/need to attend EuroPython2019"
    )
    involvement = forms.CharField(
        help_text=(
            "Describe your involvement in any open source projects"
            " and/or python community"
        )
    )
    expectations = forms.CharField(
        label="What do you expect to obtain form the conference?"
    )
    portfolio = forms.CharField(
        help_text=(
            "Please provide links to any portfolios you have that contain"
            " Python work. (e.g. Github, Bitbucket, etc.)."
            " We don't expect from you a professional description,"
            " you can show us an examples of work you were working "
            "or would like to work on"
        )
    )

    how_do_you_use_python = forms.CharField(label="How do you use Python?")

    first_time_europython = forms.CharField(
        label="Is this your first time attending EuroPython conference?",
        help_text="Yes/No",
    )
    speaker_or_coach = forms.CharField(
        label="Are you a Speaker/Coach at EuroPython 2019?",
        help_text="Yes/No/I have applied but don't know yet",
    )

    did_you_volunteer = forms.CharField(
        label="Did you join a volunteer initiative last years?",
    )

    supplements = forms.CharField(
        widget=forms.Textarea,
        help_text="Any additional information that might be helpful"
    )
