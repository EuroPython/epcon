from datetime import timedelta

from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Div, Layout, Submit, HTML
from phonenumber_field.formfields import PhoneNumberField
from model_utils import Choices

from django import forms
from django.conf.urls import url as re_path
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Q, Case, When, Value, BooleanField
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse

from assopy.models import Invoice, Order
from p3.models import P3Profile, TicketConference
from p3.utils import assign_ticket_to_user

from .accounts import get_or_create_attendee_profile_for_new_user
from .cfp import AddSpeakerToTalkForm
from .models import (
    AttendeeProfile,
    TALK_STATUS,
    Conference,
    Speaker,
    TalkSpeaker,
    Ticket,
    ATTENDEEPROFILE_VISIBILITY,
    ATTENDEEPROFILE_GENDER,
)
from .tickets import reset_ticket_settings
from .decorators import full_profile_required


@login_required
@full_profile_required
def user_dashboard(request):
    proposals = get_proposals_for_current_conference(request.user)
    orders = get_orders_for_current_conference(request.user)
    invoices = get_invoices_for_current_conference(request.user)
    tickets = get_tickets_for_current_conference(request.user)

    return TemplateResponse(
        request,
        "conference/user_panel/dashboard.html",
        {
            # Because in the template TALK_STATUS.accepted will be expanded to
            # the verbose name, and therefore comparison in the template will
            # fail. Putting that in a separate variable.
            "ACCEPTED_PROPOSAL": TALK_STATUS.accepted,
            "proposals": proposals,
            "orders": orders,
            "invoices": invoices,
            "tickets": tickets,
        },
    )


@login_required
def manage_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if not ticket.fare.is_conference or ticket not in get_tickets_for_current_conference(user=request.user):
        return HttpResponse("Can't do", status=403)

    ticket_configuration, _ = TicketConference.objects.get_or_create(
        ticket=ticket, defaults={"name": ticket.name}
    )

    ticket_configuration_form = TicketConferenceConfigForm(
        instance=ticket_configuration, initial={"name": ticket.name}
    )

    if request.method == "POST":
        ticket_configuration_form = TicketConferenceConfigForm(
            request.POST, instance=ticket_configuration
        )

        if ticket_configuration_form.is_valid():
            with transaction.atomic():
                ticket_configuration_form.save()
                # copy name
                ticket.name = ticket_configuration.name
                ticket.save()
                messages.success(request, "Ticket configured!")
                return redirect("user_panel:dashboard")

    return TemplateResponse(
        request,
        "conference/user_panel/configure_ticket.html",
        {"ticket_configuration_form": ticket_configuration_form, "ticket": ticket},
    )


@login_required
def assign_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if ticket.buyer != request.user or ticket not in get_tickets_for_current_conference(user=request.user):
        return HttpResponse("Can't do", status=403)

    assignment_form = AssignTicketForm(initial={'email': ticket.assigned_email})

    if request.method == "POST":
        assignment_form = AssignTicketForm(request.POST)

        if assignment_form.is_valid():
            user = assignment_form.get_user()
            with transaction.atomic():
                assign_ticket_to_user(ticket, user)
                reset_ticket_settings(ticket)

            messages.success(
                request, "Ticket successfuly reassigned to %s" % user.email
            )
            return redirect("user_panel:dashboard")

    return TemplateResponse(
        request,
        "conference/user_panel/assign_ticket.html",
        {"ticket": ticket, "assignment_form": assignment_form},
    )


@login_required
def privacy_settings(request):
    attendee_profile = get_or_create_attendee_profile_for_new_user(user=request.user)
    p3_profile = attendee_profile.p3_profile

    privacy_form = ProfileSpamControlForm(instance=p3_profile)

    if request.method == "POST":
        privacy_form = ProfileSpamControlForm(instance=p3_profile, data=request.POST)
        if privacy_form.is_valid():
            privacy_form.save()

    return TemplateResponse(
        request,
        "conference/user_panel/privacy_settings.html",
        {"privacy_form": privacy_form},
    )


@login_required
def profile_settings(request):
    attendee_profile = get_or_create_attendee_profile_for_new_user(user=request.user)

    profile_form = ProfileSettingsForm(instance=attendee_profile)

    if request.method == "POST":
        profile_form = ProfileSettingsForm(
            instance=attendee_profile, data=request.POST, files=request.FILES
        )
        if profile_form.is_valid():
            profile_form.save()
            # Read the saved data back to make sure things get saved correctly
            profile_form = ProfileSettingsForm(instance=attendee_profile)

    return TemplateResponse(
        request,
        "conference/user_panel/profile_settings.html",
        {"profile_form": profile_form},
    )


class AssignTicketForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        try:
            self.get_user()
        except User.DoesNotExist:
            raise forms.ValidationError(
                "Sorry, user does not exist in our system. "
                "Please ask them to create an account first"
            )

        return self.cleaned_data["email"]

    def get_user(self):
        return User.objects.get(
            is_active=True,
            email__iexact=self.cleaned_data["email"],
        )


class CommaStringMultipleChoiceField(forms.MultipleChoiceField):
    def to_python(self, value):
        return [val.rstrip().lstrip() for val in value.split(",")]

    def clean(self, value):
        return ",".join([val.rstrip().lstrip() for val in value])


class TicketConferenceConfigForm(forms.ModelForm):

    days = CommaStringMultipleChoiceField(
        label="Days of attendance",
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )
    name = forms.CharField(
        help_text="Please contact support to update how your name is displayed on your ticket.",
        disabled=True,
    )

    class Meta:
        model = TicketConference
        fields = ["name", "diet", "shirt_size", "tagline", "days"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["days"].choices = self.conference_days()

    def conference_days(self):
        conference = Conference.objects.current()
        choices = []
        date = conference.conference_start
        while date <= conference.conference_end:
            choices.append((str(date), date.strftime("%A %d %B %Y")))
            date += timedelta(days=1)
        return choices


class ProfileSpamControlForm(forms.ModelForm):
    spam_recruiting = forms.BooleanField(
        label="I want to receive a few selected job offers through EuroPython.",
        required=False,
    )
    spam_user_message = forms.BooleanField(
        label="I want to receive private messages from other participants.",
        required=False,
    )
    spam_sms = forms.BooleanField(
        label="I want to receive SMS during the conference for main communications.",
        required=False,
    )

    class Meta:
        model = P3Profile
        fields = ("spam_recruiting", "spam_user_message", "spam_sms")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                "spam_recruiting",
                template="conference/user_panel/forms/privacy_settings_recruiting.html",
            ),
            Div(
                "spam_user_message",
                template="conference/user_panel/forms/privacy_settings_user_messages.html",
            ),
            Div(
                "spam_sms",
                template="conference/user_panel/forms/privacy_settings_sms_messages.html",
            ),
            ButtonHolder(Submit("update", "Update", css_class="btn btn-primary")),
        )


PICTURE_CHOICES = Choices(
    ("none", "Do not show any picture"),
    ("gravatar", "Use my Gravatar"),
    ("url", "Use this url"),
    ("file", "Use this picture"),
)


class ProfileSettingsForm(forms.ModelForm):
    # TODO move this form and AddSpeakerToTalkForm forms to a separate file
    #  and define a common ancestor as they share some of the fields
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    phone = PhoneNumberField(
        help_text=(
            "We require a mobile phone number for all speakers "
            "for last minute contacts and in case we need "
            "timely clarification (if no reponse to previous emails). "
            "Use the international format (e.g.: +44 123456789). "
            "This field will <strong>never</strong> be published."
        ),
        max_length=30,
        required=False,
    )
    gender = forms.ChoiceField(
        help_text=(
            "We use this information for statistics related to conference "
            "attendance diversity. "
            "This field will <strong>never</strong> be published."
        ),
        choices=(("", "", ""),) + ATTENDEEPROFILE_GENDER,
        widget=forms.Select,
        required=True,
    )

    is_minor = AddSpeakerToTalkForm.base_fields["is_minor"]
    job_title = AddSpeakerToTalkForm.base_fields["job_title"]
    company = AddSpeakerToTalkForm.base_fields["company"]
    company_homepage = AddSpeakerToTalkForm.base_fields["company_homepage"]

    bio = forms.CharField(
        label="Compact biography",
        help_text="Short biography (one or two paragraphs). Do not paste your CV",
        widget=forms.Textarea,
        required=False,
    )
    tagline = forms.CharField(
        label="Tagline", help_text="Describe yourself in one line.", required=False
    )
    twitter = forms.CharField(max_length=80, required=False)
    visibility = forms.ChoiceField(
        label="",
        choices=ATTENDEEPROFILE_VISIBILITY,
        widget=forms.RadioSelect,
        required=False,
    )

    # The following fields are rendered manually, not using crispy forms, in
    # order to have more control over their layout.
    picture_options = forms.ChoiceField(
        label="", choices=PICTURE_CHOICES, required=False, widget=forms.RadioSelect
    )
    image_url = forms.URLField(required=False)
    image = forms.FileField(required=False, widget=forms.FileInput)

    class Meta:
        model = AttendeeProfile
        fields = (
            # first section
            "first_name",
            "last_name",
            "is_minor",
            "phone",
            "gender",
            "email",
            # second section
            "picture_options",
            "image_url",
            "image",
            # third section
            "tagline",
            "twitter",
            "personal_homepage",
            "location",
            "job_title",
            "company",
            "company_homepage",
            "bio",
            # fourth section
            "visibility",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the initial values for fields that are not part of AttendeeProfile
        user = self.instance.user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["email"].initial = user.email

        p3_profile = self.instance.p3_profile
        self.fields["tagline"].initial = p3_profile.tagline
        self.fields["twitter"].initial = p3_profile.twitter

        self.fields["bio"].initial = getattr(self.instance.getBio(), "body", "")

        # Determine the value of the image fields
        image_url = self.instance.p3_profile.profile_image_url()
        if self.instance.image:
            selected_image_option = PICTURE_CHOICES.file
        elif p3_profile.image_url:
            selected_image_option = PICTURE_CHOICES.url
        elif p3_profile.image_gravatar:
            selected_image_option = PICTURE_CHOICES.gravatar
        else:
            selected_image_option = PICTURE_CHOICES.none

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML("<h1>Personal information</h1>"),
            Div(
                Div("first_name", css_class="col-md-6"),
                Div("last_name", css_class="col-md-6"),
                css_class="row",
            ),
            Div(
                Div("email", css_class="col-md-6"),
                Div("is_minor", css_class="col-md-6 mt-4"),
                css_class="row",
            ),
            Div(
                Div("phone", css_class="col-md-6"),
                Div("gender", css_class="col-md-6"),
                css_class="row",
            ),
            HTML("<h1>Profile picture</h1>"),
            Div(
                HTML(
                    render_to_string(
                        "conference/user_panel/forms/profile_settings_picture.html",
                        context={
                            "selected_picture_option": selected_image_option,
                            "profile_image_url": image_url,
                            # Creating an enum-type accessible in the template
                            "picture_choices": dict(
                                [(x[0], x[0]) for x in PICTURE_CHOICES]
                            ),
                        },
                    )
                ),
                css_class="row",
            ),
            HTML("<h1>Profile information</h1>"),
            Div(Div("tagline", css_class="col-md-12"), css_class="row"),
            Div(
                Div("personal_homepage", css_class="col-md-4"),
                Div("twitter", css_class="col-md-4"),
                Div("location", css_class="col-md-4"),
                css_class="row",
            ),
            Div(
                Div("job_title", css_class="col-md-4"),
                Div("company", css_class="col-md-4"),
                Div("company_homepage", css_class="col-md-4"),
                css_class="row",
            ),
            Div(Div("bio", css_class="col-md-12"), css_class="row"),
            HTML("<h1>Profile page visibility</h1>"),
            HTML(
                "<h5><strong>Speaker profile pages are public by default.</strong> If you are giving a talk or"
                " training at this year's conference, you can still set your preferences for the following years.</h5>"
            ),
            Div(Div("visibility", css_class="col-md-4"), css_class="row"),
            ButtonHolder(
                Submit("update", "Update", css_class="btn btn-lg btn-primary")
            ),
        )

    def clean_email(self):
        value = self.cleaned_data["email"].strip()
        user = self.instance.user

        if value != user.email and User.objects.filter(email__iexact=value).exists():
            raise forms.ValidationError("Email already registered")

        return value

    def clean_twitter(self):
        data = self.cleaned_data.get("twitter", "")
        if data.startswith("@"):
            data = data[1:]
        return data

    def resolve_image_settings(self, selected_option, image_url, image):
        if selected_option == PICTURE_CHOICES.gravatar:
            image = None
            image_url = ""
            image_gravatar = True
        elif selected_option == PICTURE_CHOICES.url:
            image = None
            image_gravatar = False
        elif selected_option == PICTURE_CHOICES.file:
            image_url = ""
            image_gravatar = False
        else:
            # The default, or when the user selects PICTURE_CHOICES.none
            image = None
            image_url = ""
            image_gravatar = False

        return image_gravatar, image_url, image

    def save(self, commit=True):
        """
        Since this form updates related models, it does not support commit=False.
        """
        profile = super().save(commit=True)
        profile.setBio(self.cleaned_data.get("bio", ""))

        # Resolve image settings.
        image_gravatar, image_url, image = self.resolve_image_settings(
            selected_option=self.cleaned_data["picture_options"],
            image_url=self.cleaned_data.get("image_url"),
            image=self.cleaned_data.get("image"),
        )
        profile.image = image
        profile.save()

        # Save user fields
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.save()

        # Save p3 profile fields
        p3_profile = profile.p3_profile
        p3_profile.tagline = self.cleaned_data["tagline"]
        p3_profile.twitter = self.cleaned_data["twitter"]
        p3_profile.image_gravatar = image_gravatar
        p3_profile.image_url = image_url
        p3_profile.save()

        return profile


def get_tickets_for_current_conference(user):
    conference = Conference.objects.current()
    return Ticket.objects.filter(
        Q(fare__conference=conference.code)
        & Q(frozen=False)
        & Q(orderitem__order___complete=True)
        & (Q(user=user) | Q(orderitem__order__user__pk=user.assopy_user.pk))
    ).annotate(
        is_buyer=Case(
            When(orderitem__order__user__pk=user.assopy_user.pk, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )


def get_invoices_for_current_conference(user):
    return Invoice.objects.filter(
        order__user__user=user,
        emit_date__year=Conference.objects.current().conference_start.year,
    )


def get_proposals_for_current_conference(user):
    """
    This goes through TalkSpeaker module, not Talk.created_by to correctly show
    cases if people are assigned (as co-speakers) to proposals/talks created by
    other people
    """

    try:
        speaker = user.speaker
    except Speaker.DoesNotExist:
        return None

    talkspeakers = TalkSpeaker.objects.filter(
        speaker=speaker, talk__conference=Conference.objects.current().code
    )

    return [ts.talk for ts in talkspeakers]


def get_orders_for_current_conference(user):
    # HACK(artcz) -- because Order doesn't have a link to Conference, we'll
    # just filter by current's conference year
    year = Conference.objects.current().conference_start.year
    return Order.objects.filter(created__year=year, user=user.assopy_user)


urlpatterns = [
    re_path(r"^$", user_dashboard, name="dashboard"),
    re_path(r"^manage-ticket/(?P<ticket_id>\d+)/$", manage_ticket, name="manage_ticket"),
    re_path(r"^assign-ticket/(?P<ticket_id>\d+)/$", assign_ticket, name="assign_ticket"),
    re_path(r"^privacy-settings/$", privacy_settings, name="privacy_settings"),
    re_path(r"^profile-settings/$", profile_settings, name="profile_settings"),
    re_path(
        r"^password/change/$",
        auth_views.PasswordChangeView.as_view(
            template_name="conference/user_panel/password_change.html",
            success_url=reverse_lazy("user_panel:password_change_done"),
        ),
        name="password_change",
    ),
    re_path(
        r"^password/change/done/$",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="conference/user_panel/password_change_done.html"
        ),
        name="password_change_done",
    ),
]
