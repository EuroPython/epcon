from django import forms
from django.conf import settings
from django.conf.urls import url as re_path
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.generic import RedirectView

from phonenumber_field.formfields import PhoneNumberField

from .forms import ProposalForm
from .models import (
    Conference,
    AttendeeProfile,
    Speaker,
    Talk,
    TalkSpeaker,
    Ticket,
)
from .talks import dump_relevant_talk_information_to_dict
from .decorators import full_profile_required
from conference.fares import SPEAKER_TICKET_CODE_REGEXP

@login_required
@full_profile_required
def submit_proposal_step1_talk_info(request):
    """
    Main submit_proposal view
    """
    conf = Conference.objects.current()
    if not conf.cfp():
        return TemplateResponse(request, "conference/cfp/cfp_is_closed.html", {
            'conf': conf
        })

    proposal_form = ProposalForm()

    if request.method == "POST":
        proposal_form = ProposalForm(request.POST)

        if proposal_form.is_valid():
            with transaction.atomic():
                talk = proposal_form.save(request.user)
                messages.success(
                    request,
                    "Proposal added, now please add information about the speaker",
                )
                send_talk_details_to_backup_email(talk)
                return redirect("cfp:step2_add_speakers", talk_uuid=talk.uuid)

    return TemplateResponse(request, "conference/cfp/step1_talk_info.html", {
        "proposal_form": proposal_form,
    })


def send_talk_details_to_backup_email(talk: Talk):
    """
    This is just to double check if we're not loosing any proposals, based on
    the feedback we've seen on telegram
    """
    SEND_CFP_BACKUP_TO = ['web-wg@europython.eu']

    content = f"""
    title: {talk.title}
    author: {talk.created_by.id}
    type_display: {talk.get_type_display()}
    subtitle: {talk.sub_title},
    abstract_short: {talk.abstract_short}
    abstract: {talk.getAbstract().body}
    abstract_extra: {talk.abstract_extra}
    """

    send_mail(
        subject=f"New Proposal for EP CFP #{talk.id}",
        message=content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=SEND_CFP_BACKUP_TO,
    )


@login_required
@full_profile_required
def submit_proposal_step2_add_speakers(request, talk_uuid):
    """
    Step2 of adding proposal - information about the speakers
    """
    talk = get_object_or_404(Talk, uuid=talk_uuid)

    speaker_form = AddSpeakerToTalkForm(
        initial=extract_initial_speaker_data_from_user(request.user)
    )

    if request.method == 'POST':
        speaker_form = AddSpeakerToTalkForm(request.POST)
        if speaker_form.is_valid():
            with transaction.atomic():
                speaker = save_information_from_speaker_form(
                    request.user, speaker_form.cleaned_data
                )
                add_speaker_to_talk(speaker, talk)
                messages.success(request, "Speaker added successfully.")
                return redirect("cfp:step3_thanks", talk_uuid=talk.uuid)

    return TemplateResponse(request, "conference/cfp/step2_add_speaker.html", {
        "talk": talk,
        "speaker_form": speaker_form,
    })


@login_required
@full_profile_required
def submit_proposal_step3_thanks(request, talk_uuid):
    """
    Step3 - thanks for proposal
    """
    talk = get_object_or_404(Talk, uuid=talk_uuid)
    speakers = list(talk.get_all_speakers())
    speaker_emails = [speaker.user.email for speaker in speakers]
    speaker_names = ",".join(
        [f"{speaker.user.first_name} {speaker.user.last_name}" for speaker in speakers]
    )
    current_site = get_current_site(request)
    cfp_path = reverse_lazy("cfp:preview", args=[talk.slug])
    proposal_url = f"https://{current_site}{cfp_path}"
    content = f"""
    Hi {speaker_names}!
    We have received your submission "{talk.title}".
    We will notify you once we have had time to consider all submissions,
    but until then you can see and edit your submission at {proposal_url}

    Please do not hesitate to contact us at at helpdesk@europython.eu if you have any questions!
    """
    send_mail(
        subject=f"Your submission to {settings.CONFERENCE_NAME}: {talk.title}",
        message=content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=speaker_emails,
    )
    return TemplateResponse(
        request, "conference/cfp/step3_thanks.html", {"talk": talk,}
    )


@login_required
@full_profile_required
def update_proposal(request, talk_uuid):
    """
    Update/Edit proposal view
    """
    talk = get_object_or_404(Talk, uuid=talk_uuid)

    if not talk.created_by == request.user:
        return HttpResponseForbidden()

    conf = Conference.objects.current()
    if not conf.cfp():
        return HttpResponseForbidden()

    proposal_edit_form = ProposalForm(instance=talk)

    if request.method == 'POST':
        proposal_edit_form = ProposalForm(request.POST, instance=talk)

        if proposal_edit_form.is_valid():
            proposal_edit_form.save(request.user)
            messages.success(request, "Proposal updated")
            return redirect('cfp:preview', talk_slug=talk.slug)

    return TemplateResponse(request, "conference/cfp/update_proposal.html", {
        "talk": talk,
        "proposal_edit_form": proposal_edit_form,
    })


@login_required
@full_profile_required
def update_speakers(request, talk_uuid):
    """
    Update/Edit proposal's speaker(s) view
    """
    talk = get_object_or_404(Talk, uuid=talk_uuid)

    if not talk.created_by == request.user:
        return HttpResponseForbidden()

    conf = Conference.objects.current()
    if not conf.cfp():
        return HttpResponseForbidden()

    speaker_form = UpdateAttendeeProfile(
        initial=extract_initial_speaker_data_from_user(request.user)
    )

    if request.method == 'POST':
        speaker_form = UpdateAttendeeProfile(request.POST)
        if speaker_form.is_valid():
            with transaction.atomic():
                save_information_from_speaker_form(
                    request.user, speaker_form.cleaned_data
                )
                messages.success(request, "Speaker updated successfully.",)
                return redirect("cfp:preview", talk_slug=talk.slug)

    return TemplateResponse(request, "conference/cfp/update_speakers.html", {
        "talk": talk,
        "speaker_edit_form": speaker_form,
    })


@login_required
def preview_proposal(request, talk_slug):
    """
    Preview proposal
    """
    talk = get_object_or_404(Talk, slug=talk_slug)
    talk_as_dict = dump_relevant_talk_information_to_dict(talk)
    conf = Conference.objects.current()
    return TemplateResponse(request, "conference/cfp/preview.html", {
        "talk": talk,
        "talk_as_dict": talk_as_dict,
        "cfp_is_open": conf.cfp(),
    })


@login_required
@staff_member_required
def program_wg_download_all_talks_for_current_conference(request):
    """
    TODO: add some permission checks here
    """
    current_conf = Conference.objects.current()
    talks = dump_all_talks_for_conference_to_dict(current_conf)
    #print ('talks = %r' % talks)
    return JsonResponse({'talks': talks})


def extract_initial_speaker_data_from_user(user):
    attendee = user.attendeeprofile

    given_name, family_name = user.assopy_user.name_tuple()
    return {
        'users_given_name': given_name,
        'users_family_name': family_name,
        'is_minor': attendee.is_minor,
        'job_title': attendee.job_title,
        'bio': getattr(attendee.getBio(), "body", ""),
        'company': attendee.company,
        'company_homepage': attendee.company_homepage,
        'phone': attendee.phone,
        'location': attendee.location,
    }


def dump_all_talks_for_conference_to_dict(conference: Conference):

    talks = Talk.objects.filter(conference=conference.code)
    ticket_data = Ticket.objects.filter(
        fare__conference=conference,
        fare__ticket_type='conference',
        orderitem__order___complete=True,
        fare__code__regex=SPEAKER_TICKET_CODE_REGEXP,
        frozen=False,
        )
    speaker_tickets = dict(
        (ticket.p3_conference.assigned_to, ticket)
        for ticket in ticket_data)
    output = [
        dump_relevant_talk_information_to_dict(talk,
                                               speaker_tickets=speaker_tickets)
        for talk in talks
    ]
    return output


def save_information_from_speaker_form(user, cleaned_data):
    user.first_name = cleaned_data['users_given_name']
    user.last_name = cleaned_data['users_family_name']
    user.save()

    ap = user.attendeeprofile
    ap.phone = cleaned_data['phone']
    ap.is_minor = cleaned_data['is_minor']
    ap.job_title = cleaned_data['job_title']
    ap.company = cleaned_data['company']
    ap.company_homepage = cleaned_data['company_homepage']
    ap.setBio(cleaned_data['bio'])
    ap.save()

    speaker, _ = Speaker.objects.get_or_create(user=user)
    return speaker


def add_speaker_to_talk(speaker, talk):
    ts, _ = TalkSpeaker.objects.get_or_create(talk=talk, speaker=speaker)
    return None


class AddSpeakerToTalkForm(forms.ModelForm):
    users_given_name = forms.CharField(label="Given name of the speaker")
    users_family_name = forms.CharField(label="Family name of the speaker")
    is_minor = forms.BooleanField(
        label="Are you a minor?",
        help_text=(
            "Please select this checkbox if you're going to be under 18"
            "years old on July 26th 2021"
        ),
        # required=False, because django forms... it means that unless someone
        # is a minor we don't provide a value.
        required=False,
    )
    job_title = forms.CharField(
        label="Job title",
        help_text="eg: student, developer, CTO, js ninja, BDFL",
        max_length=50,
        required=False,
    )
    phone = PhoneNumberField(
        help_text=(
            "We require a mobile phone number for all speakers "
            "for last minute contacts and in case we need "
            "timely clarification (if no reponse to previous emails). "
            "Use the international format (e.g.: +44 123456789). "
            "This field will <strong>never</strong> be published."
        ),
        max_length=30,
    )
    company = forms.CharField(
        label="Your company", max_length=50, required=False
    )
    company_homepage = forms.URLField(
        label="Company homepage", required=False
    )
    bio = forms.CharField(
        label="Compact biography",
        help_text=(
            "Please enter a short biography (one or two paragraphs) <br />"
            "Do not paste your CV!"
        ),
        widget=forms.Textarea(),
    )

    class Meta:
        model = AttendeeProfile
        fields = [
            'users_given_name',
            'users_family_name',
            'job_title',
            'is_minor',
            'phone',
            'bio',
            'company',
            'company_homepage',
        ]


class UpdateAttendeeProfile(AddSpeakerToTalkForm):
    pass


urlpatterns = [
    re_path(
        r'^$',
        RedirectView.as_view(url=reverse_lazy("cfp:step1_submit_proposal"))
    ),
    re_path(
        r"^submit-proposal/$",
        submit_proposal_step1_talk_info,
        name="step1_submit_proposal",
    ),
    re_path(
        r"^submit-proposal/(?P<talk_uuid>[\w-]+)/add-speakers/$",
        submit_proposal_step2_add_speakers,
        name="step2_add_speakers",
    ),
    re_path(
        r"^submit-proposal/(?P<talk_uuid>[\w-]+)/thanks/$",
        submit_proposal_step3_thanks,
        name="step3_thanks",
    ),
    re_path(
        r"^preview/(?P<talk_slug>[\w-]+)/$",
        preview_proposal,
        name="preview",
    ),
    re_path(
        r"^update/(?P<talk_uuid>[\w-]+)/speakers/$",
        update_speakers,
        name="update_speakers",
    ),
    re_path(
        r"^update/(?P<talk_uuid>[\w-]+)/$",
        update_proposal,
        name="update",
    ),
    re_path(
        r"^program-wg/download-all-talks/$",
        program_wg_download_all_talks_for_current_conference,
        name="program_wg_download_all_talks",
    ),
]
