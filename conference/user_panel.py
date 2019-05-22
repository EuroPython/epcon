from datetime import timedelta

from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    ButtonHolder,
    Div,
    Layout,
    Submit,
    HTML,
    Field,
)
from phonenumber_field.formfields import PhoneNumberField

from django import forms
from django.conf.urls import url
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse_lazy
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.template.loader import render_to_string
from django.template.response import TemplateResponse

from assopy.models import (
    Invoice,
    Order,
)
from conference.accounts import get_or_create_attendee_profile_for_new_user
from conference.cfp import AddSpeakerToTalkForm
from conference.models import (
    AttendeeProfile,
    TALK_STATUS,
    Conference,
    Speaker,
    TalkSpeaker,
    Ticket,
    ATTENDEEPROFILE_VISIBILITY,
)
from conference.tickets import (
    assign_ticket_to_user,
    reset_ticket_settings,
)
from p3.models import (
    P3Profile,
    TicketConference,
)


@login_required
def user_dashboard(request):
    proposals = get_proposals_for_current_conference(request.user)
    orders = get_orders_for_current_conference(request.user)
    invoices = get_invoices_for_current_conference(request.user)
    tickets = get_tickets_for_current_conference(request.user)

    return TemplateResponse(
        request,
        "ep19/bs/user_panel/dashboard.html",
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

    if ticket.user != request.user:
        return HttpResponse("Can't do", status=403)

    ticket_configuration, _ = TicketConference.objects.get_or_create(
        ticket=ticket,
        defaults={'name': ticket.name})

    ticket_configuration_form = TicketConferenceConfigForm(
        instance=ticket_configuration, initial={"name": request.user.assopy_user.name()}
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
        "ep19/bs/user_panel/configure_ticket.html",
        {"ticket_configuration_form": ticket_configuration_form, "ticket": ticket},
    )


@login_required
def assign_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if ticket.user != request.user:
        return HttpResponse("Can't do", status=403)

    assignment_form = AssignTicketForm()

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
        "ep19/bs/user_panel/assign_ticket.html",
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
        "ep19/bs/user_panel/privacy_settings.html",
        {"privacy_form": privacy_form},
    )


@login_required
def profile_settings(request):
    attendee_profile = get_or_create_attendee_profile_for_new_user(user=request.user)

    profile_form = ProfileSettingsForm(instance=attendee_profile)

    return TemplateResponse(
        request,
        "ep19/bs/user_panel/profile_settings.html",
        {"profile_form": profile_form}
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
        return User.objects.get(email=self.cleaned_data["email"])


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
                template="ep19/bs/user_panel/forms/privacy_settings_recruiting.html",
            ),
            Div(
                "spam_user_message",
                template="ep19/bs/user_panel/forms/privacy_settings_user_messages.html",
            ),
            Div(
                "spam_sms",
                template="ep19/bs/user_panel/forms/privacy_settings_sms_messages.html",
            ),
            ButtonHolder(Submit("update", "Update", css_class="btn btn-primary")),
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
            "timely clarification (if no reponse to previous emails).<br>"
            "Use the international format, eg: +39-055-123456.<br />"
            "This number will <strong>never</strong> be published."
        ),
        max_length=30,
        required=False,
    )

    is_minor = AddSpeakerToTalkForm.base_fields["is_minor"]

    job_title = AddSpeakerToTalkForm.base_fields["job_title"]
    company = AddSpeakerToTalkForm.base_fields["company"]
    company_homepage = AddSpeakerToTalkForm.base_fields["company_homepage"]

    bio = forms.CharField(
        label='Compact biography',
        help_text='Short biography (one or two paragraphs). Do not paste your CV',
        widget=forms.Textarea,
        required=False,)
    tagline = forms.CharField(
        label='Tagline',
        help_text='Describe yourself in one line.',
        required=False,
    )
    twitter = forms.CharField(max_length=80, required=False)
    visibility = forms.ChoiceField(label='', choices=ATTENDEEPROFILE_VISIBILITY, widget=forms.RadioSelect, required=False)

    # The following fields are rendered manually, not using crispy forms, in
    # order to have more control over their layout.
    picture_options = forms.ChoiceField(label='', choices=(
        ('none', 'Do not show any picture'),
        ('gravatar', 'Use my Gravatar'),
        ('url', 'Use this url'),
        ('file', 'Use this picture'),
    ), required=False, widget=forms.RadioSelect)
    image_url = forms.URLField(required=False)
    image = forms.FileField(required=False, widget=forms.FileInput)

    class Meta:
        model = AttendeeProfile
        fields = (
            # first section
            "first_name", "last_name", "is_minor", "phone", "email",
            # second section
            'picture_options', 'image_url', 'image',
            # third section
            "tagline", "twitter", "personal_homepage", "location",
            "job_title", "company", "company_homepage", "bio",
            # fourth section
            "visibility",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the initial values for fields that are not part of AttendeeProfile
        user = self.instance.user
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['email'].initial = user.email

        p3_profile = self.instance.p3_profile
        self.fields['tagline'].initial = p3_profile.tagline
        self.fields['twitter'].initial = p3_profile.twitter

        self.fields['bio'].initial = getattr(self.instance.getBio(), 'body', '')

        # Determine the value of the image fields
        image_url = self.instance.p3_profile.profile_image_url()
        if self.instance.image:
            selected_image_option = 'file'
        elif p3_profile.image_url:
            selected_image_option = 'url'
        elif p3_profile.image_gravatar:
            selected_image_option = 'gravatar'
        else:
            selected_image_option = 'none'

        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML("<h1>Personal information</h1>"),
            Div(
                Div('first_name', css_class='col-md-6'),
                Div('last_name', css_class='col-md-6'),
                css_class='row'
            ),
            Div(
                Div('email', css_class='col-md-6'),
                Div('phone', css_class='col-md-6'),
                css_class='row'
            ),
            Div(
                Div('is_minor', css_class='col-md-6'),
                css_class='row'
            ),
            HTML("<h1>Profile picture</h1>"),
            Div(
                HTML(
                    render_to_string('ep19/bs/user_panel/forms/profile_settings_picture.html', context={
                        'selected_picture_option': selected_image_option,
                        'profile_image_url': image_url,
                    }),
                ),
                css_class='row',
            ),
            HTML("<h1>Profile information</h1>"),
            Div(
                Div('tagline', css_class='col-md-12'),
                css_class='row'
            ),
            Div(
                Div('personal_homepage', css_class='col-md-4'),
                Div('twitter', css_class='col-md-4'),
                Div('location', css_class='col-md-4'),
                css_class='row'
            ),
            Div(
                Div('job_title', css_class='col-md-4'),
                Div('company', css_class='col-md-4'),
                Div('company_homepage', css_class='col-md-4'),
                css_class='row'
            ),
            Div(
                Div('bio', css_class='col-md-12'),
                css_class='row'
            ),
            HTML("<h1>Profile page visibility</h1>"),
            HTML("<h5>Note that if you are giving a talk or training at this year's conference,"
                 " this setting will not have any effect as <strong>speaker pages are public by default.</strong></h5>"),
            HTML("<h5>You can still set your preferences for the following years.</h5>"),
            Div(
                Div('visibility', css_class='col-md-4'),
                css_class="row",
            ),
            ButtonHolder(Submit("update", "Update", css_class="btn btn-lg btn-primary")),
        )

    def clean_email(self):
        value = self.cleaned_data['email'].strip()
        user = self.instance.user

        if value != user.email and User.objects.filter(email__iexact=value).exists():
            raise forms.ValidationError('Email already registered')

        return value


def get_tickets_for_current_conference(user):
    conference = Conference.objects.current()
    return Ticket.objects.filter(
        Q(fare__conference=conference.code)
        & Q(orderitem__order___complete=True)
        & Q(user=user)
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
    url(r"^$", user_dashboard, name="dashboard"),
    url(r"^manage-ticket/(?P<ticket_id>\d+)/$", manage_ticket, name="manage_ticket"),
    url(r"^assign-ticket/(?P<ticket_id>\d+)/$", assign_ticket, name="assign_ticket"),
    url(r"^privacy-settings/$", privacy_settings, name="privacy_settings"),
    url(r"^profile-settings/$", profile_settings, name="profile_settings"),
    # Password change, using default django views.
    # TODO(artcz): Those are Removed in Django21 and we should replcethem with
    # class based PasswordChange{,Done}View
    url(
        r"^password/change/$",
        auth_views.password_change,
        kwargs={
            "template_name": "ep19/bs/user_panel/password_change.html",
            "post_change_redirect": reverse_lazy("user_panel:password_change_done"),
        },
        name="password_change",
    ),
    url(
        r"^password/change/done/$",
        auth_views.password_change_done,
        kwargs={"template_name": "ep19/bs/user_panel/password_change_done.html"},
        name="password_change_done",
    ),
]
