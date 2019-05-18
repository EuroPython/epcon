from django import forms
from django.conf import settings
from django.conf.urls import url
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.urlresolvers import reverse_lazy
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import slugify
from django.template.response import TemplateResponse
from django.views.generic import RedirectView

from taggit.forms import TagField
from taggit_labels.widgets import LabelWidget
from phonenumber_field.formfields import PhoneNumberField

from conference.forms import TalkBaseForm
from conference.models import (
    Conference,
    ConferenceTag,
    AttendeeProfile,
    Speaker,
    Talk,
    TALK_TYPE,
    TalkSpeaker,
)
from conference.talks import dump_relevant_talk_information_to_dict


@login_required
def submit_proposal_step1_talk_info(request):
    """
    Main submit_proposal view for ep2019+
    """

    conf = Conference.objects.current()
    if not conf.cfp():
        return TemplateResponse(request, "ep19/bs/cfp/cfp_is_closed.html", {
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
                    "Proposal added, "
                    "now please add information about the speaker",
                )
                send_talk_details_to_backup_email(talk)
                return redirect("cfp:step2_add_speakers", talk_uuid=talk.uuid)

    return TemplateResponse(request, "ep19/bs/cfp/step1_talk_info.html", {
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

                messages.success(
                    request,
                    "Speaker added successfully.",
                )
                return redirect("cfp:step3_thanks", talk_uuid=talk.uuid)

    return TemplateResponse(request, "ep19/bs/cfp/step2_add_speaker.html", {
        "talk": talk,
        "speaker_form": speaker_form,
    })


@login_required
def submit_proposal_step3_thanks(request, talk_uuid):
    """
    Step3 - thanks for proposal
    """

    talk = get_object_or_404(Talk, uuid=talk_uuid)
    return TemplateResponse(request, "ep19/bs/cfp/step3_thanks.html", {
        "talk": talk,
    })


@login_required
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
            messages.success(
                request,
                "Proposal updated"
            )
            return redirect('cfp:preview', talk_slug=talk.slug)

    return TemplateResponse(request, "ep19/bs/cfp/update_proposal.html", {
        "talk": talk,
        "proposal_edit_form": proposal_edit_form,
    })


@login_required
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

                messages.success(
                    request,
                    "Speaker updated successfully.",
                )
                return redirect("cfp:preview", talk_slug=talk.slug)

    return TemplateResponse(request, "ep19/bs/cfp/update_speakers.html", {
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
    return TemplateResponse(request, "ep19/bs/cfp/preview.html", {
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
    return JsonResponse({'talks': talks})


def extract_initial_speaker_data_from_user(user):
    attendee = user.attendeeprofile

    return {
        'users_given_name': user.assopy_user.name(),
        'is_minor': attendee.is_minor,
        'gender': attendee.gender,
        'job_title': attendee.job_title,
        'bio': getattr(attendee.getBio(), "body", ""),
        'company': attendee.company,
        'company_homepage': attendee.company_homepage,
        'phone': attendee.phone,
    }


def dump_all_talks_for_conference_to_dict(conference: Conference):

    talks = Talk.objects.filter(conference=conference.code)
    output = [
        dump_relevant_talk_information_to_dict(talk)
        for talk in talks
    ]
    return output


def save_information_from_speaker_form(user, cleaned_data):
    user.first_name = cleaned_data['users_given_name']
    user.last_name = ''
    user.save()

    ap = user.attendeeprofile
    ap.phone = cleaned_data['phone']
    ap.is_minor = cleaned_data['is_minor']
    ap.gender = cleaned_data['gender']
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

    users_given_name = forms.CharField(label="Name of the speaker")
    is_minor = forms.BooleanField(
        label="Are you a minor?",
        help_text=(
            "Please select this checkbox if you're going to be under 18"
            "years old on July 8th 2019"
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
            "timely clarification (if no reponse to previous emails).<br>"
            "Use the international format, eg: +39-055-123456.<br />"
            "This number will <strong>never</strong> be published."
        ),
        max_length=30,
    )
    gender = forms.CharField(
        label="Type your gender",
        max_length=32,
        required=False,
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
            'job_title',
            'phone',
            'bio',
            'gender',
            'is_minor',
            'company',
            'company_homepage',
        ]


class UpdateAttendeeProfile(AddSpeakerToTalkForm):
    pass


class ProposalForm(forms.ModelForm):

    type = forms.ChoiceField(
        label='Type', required=True,
        choices=TALK_TYPE,
    )

    # Talk tags
    tags = TagField(required=True, widget=LabelWidget(model=ConferenceTag))

    title = TalkBaseForm.base_fields["title"]
    sub_title = TalkBaseForm.base_fields["sub_title"]
    abstract = TalkBaseForm.base_fields["abstract"]
    abstract_short = TalkBaseForm.base_fields["abstract_short"]
    prerequisites = TalkBaseForm.base_fields["prerequisites"]
    level = TalkBaseForm.base_fields["level"]
    domain_level = TalkBaseForm.base_fields["domain_level"]
    abstract_extra = TalkBaseForm.base_fields["abstract_extra"]

    class Meta:
        model = Talk
        fields = [
            'type',
            'title',
            'sub_title',
            'abstract',
            'abstract_short',
            'prerequisites',
            'level',
            'domain_level',
            'tags',
            'abstract_extra',
        ]

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if kwargs.get('instance'):
            self.fields['abstract'].initial = (
                kwargs['instance'].getAbstract().body
            )

    def save(self, user):
        """
        We don't support commit=False on this form, because .setAbstract
        requires an object saved in db.
        """
        talk = super().save(commit=False)
        talk.created_by = user
        talk.slug = f'{talk.uuid}-{slugify(talk.title)}'
        talk.conference = Conference.objects.current().code
        talk.save()
        talk.setAbstract(self.cleaned_data['abstract'])

        if 'tags' in self.cleaned_data:
            talk.tags.set(*validate_tags(self.cleaned_data['tags']))

        return talk


def validate_tags(tags):
    """
    Returns only tags that are already present in the database
    and limits the results to 5
    """
    valid_tags = ConferenceTag.objects.filter(
        name__in=tags
    ).values_list("name", flat=True)

    tags_limited = valid_tags[:5]

    return tags_limited


urlpatterns = [
    url(
        r'^$',
        RedirectView.as_view(url=reverse_lazy("cfp:step1_submit_proposal"))
    ),
    url(
        r"^submit-proposal/$",
        submit_proposal_step1_talk_info,
        name="step1_submit_proposal",
    ),
    url(
        r"^submit-proposal/(?P<talk_uuid>[\w-]+)/add-speakers/$",
        submit_proposal_step2_add_speakers,
        name="step2_add_speakers",
    ),
    url(
        r"^submit-proposal/(?P<talk_uuid>[\w-]+)/thanks/$",
        submit_proposal_step3_thanks,
        name="step3_thanks",
    ),
    url(
        r"^preview/(?P<talk_slug>[\w-]+)/$",
        preview_proposal,
        name="preview",
    ),
    url(
        r"^update/(?P<talk_uuid>[\w-]+)/speakers/$",
        update_speakers,
        name="update_speakers",
    ),
    url(
        r"^update/(?P<talk_uuid>[\w-]+)/$",
        update_proposal,
        name="update",
    ),
    url(
        r"^program-wg/download-all-talks/$",
        program_wg_download_all_talks_for_current_conference,
        name="program_wg_download_all_talks",
    ),
]
