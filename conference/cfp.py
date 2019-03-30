import shortuuid

from django import forms
from django.conf import settings
from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.template.defaultfilters import slugify
from django.template.response import TemplateResponse
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404

from conference.forms import TalkBaseForm, validate_tags
from conference.models import (
    Conference,
    AttendeeProfile,
    Speaker,
    Talk,
    TALK_TYPE,
    TalkSpeaker,
)


@login_required
def submit_proposal_step1_talk_info(request):
    """
    Main submit_proposal view for ep2019+
    """

    proposal_form = SubmitTalkProposalForm()

    if request.method == "POST":
        proposal_form = SubmitTalkProposalForm(request.POST)

        if proposal_form.is_valid():
            with transaction.atomic():
                talk = proposal_form.save(commit=False)
                talk.created_by = request.user
                talk.slug = (
                    slugify(talk.title)
                    + "-"
                    + shortuuid.ShortUUID().random(length=6)
                )
                talk.conference = Conference.objects.current().code
                talk.save()
                messages.success(
                    request,
                    "Proposal added, now add information about speaker",
                )
                return redirect("cfp:step2_add_speakers", talk_uuid=talk.uuid)

    return TemplateResponse(request, "ep19/bs/cfp/submit_proposal.html", {
        "proposal_form": proposal_form,
    })


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
                    "Added speaker",
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
def preview_proposal(request, talk_slug):
    """
    Preview proposal
    """
    talk = get_object_or_404(Talk, slug=talk_slug)
    return TemplateResponse(request, "ep19/bs/cfp/preview.html", {
        "talk": talk,
    })


@login_required
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
        'birthday': attendee.birthday,
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


def dump_relevant_talk_information_to_dict(talk: Talk):

    output = {
        'title': talk.title,
        'uuid': talk.uuid,
        'slug': talk.slug,
        'subtitle': talk.sub_title,
        'abstract_short': talk.abstract_short,
        'abstract_extra': talk.abstract_extra,
        # TODO: tags
        'speakers': [],
    }

    for speaker in talk.get_all_speakers():
        ap = speaker.user.attendeeprofile
        output['speakers'].append({
            'name': speaker.user.assopy_user.name(),
            'company': ap.company,
            'company_homepage': ap.company_homepage,
            'bio': ap.getBio().body,
            'phone': ap.phone,
        })

    return output


def save_information_from_speaker_form(user, cleaned_data):
    user.first_name = cleaned_data['users_given_name']
    user.save()

    ap = user.attendeeprofile
    ap.phone = cleaned_data['phone']
    ap.birthday = cleaned_data['birthday']
    ap.job_title = cleaned_data['job_title']
    ap.company = cleaned_data['company']
    ap.company_homepage = cleaned_data['company_homepage']
    ap.setBio(cleaned_data['bio'])
    ap.save()

    speaker, _ = Speaker.objects.get_or_create(user=user)
    return speaker


def add_speaker_to_talk(speaker, talk):
    _, ts = TalkSpeaker.objects.get_or_create(talk=talk, speaker=speaker)
    return None


class AddSpeakerToTalkForm(forms.ModelForm):

    users_given_name = forms.CharField(label="Name of the speaker")
    birthday = forms.DateField(
        label="Date of birth",
        help_text=(
            "Format: YYYY-MM-DD<br />This date will <strong>never</strong>"
            "be published."
            "We require date of birth for speakers to accomodate for"
            " laws regarding minors."
        ),
        input_formats=("%Y-%m-%d",),
        widget=forms.DateInput(attrs={"size": 10, "maxlength": 10}),
    )
    job_title = forms.CharField(
        label="Job title",
        help_text="eg: student, developer, CTO, js ninja, BDFL",
        max_length=50,
        required=False,
    )
    # TODO: add phonenumbers validation here
    phone = forms.CharField(
        help_text=(
            "We require a mobile phone number for all speakers "
            "for last minute contacts and in case we need "
            "timely clarification (if no reponse to previous emails).<br>"
            "Use the international format, eg: +39-055-123456.<br />"
            "This number will <strong>never</strong> be published."
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
        # TODO: this whole thing needs an update...
        model = AttendeeProfile
        fields = [
            'users_given_name',
            'job_title',
            'phone',
            'bio',
            'company',
            'company_homepage',
        ]


class SubmitTalkProposalForm(forms.ModelForm):

    type = forms.ChoiceField(
        label='Type', required=True,
        choices=TALK_TYPE,
    )

    title = TalkBaseForm.base_fields["title"]
    sub_title = TalkBaseForm.base_fields["sub_title"]
    abstract = TalkBaseForm.base_fields["abstract"]
    abstract_short = TalkBaseForm.base_fields["abstract_short"]
    prerequisites = TalkBaseForm.base_fields["prerequisites"]
    level = TalkBaseForm.base_fields["level"]
    domain_level = TalkBaseForm.base_fields["domain_level"]
    tags = TalkBaseForm.base_fields["tags"]
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


class ProposalSubmissionForm(forms.Form):
    """
    Submission Form for the first paper, it will contain the fields
    which populates the user profile and the data of the talk,
    only essential data is required.
    """

    # # Speaker details
    # first_name = forms.CharField(label="First name", max_length=30)
    # last_name = forms.CharField(label="Last name", max_length=30)

    type = forms.ChoiceField(
        label='Type', required=True,
        choices=TALK_TYPE,
    )

    # Talk details
    title = TalkBaseForm.base_fields["title"]
    sub_title = TalkBaseForm.base_fields["sub_title"]
    abstract = TalkBaseForm.base_fields["abstract"]
    abstract_short = TalkBaseForm.base_fields["abstract_short"]
    prerequisites = TalkBaseForm.base_fields["prerequisites"]
    level = TalkBaseForm.base_fields["level"]
    domain_level = TalkBaseForm.base_fields["domain_level"]
    tags = TalkBaseForm.base_fields["tags"]
    abstract_extra = TalkBaseForm.base_fields["abstract_extra"]

    field_order = [
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

    def __init__(self, user, *args, **kwargs):

        try:
            profile = user.attendeeprofile

        except AttendeeProfile.DoesNotExist:
            profile = None

        data = {"first_name": user.first_name, "last_name": user.last_name}

        if profile:

            if profile.birthday is None:
                birthday_value = None

            else:
                birthday_value = profile.birthday.strftime("%Y-%m-%d")

            data.update(
                {
                    "phone": profile.phone,
                    "birthday": birthday_value,
                    "job_title": profile.job_title,
                    "company": profile.company,
                    "company_homepage": profile.company_homepage,
                    "bio": getattr(profile.getBio(), "body", ""),
                }
            )

        data.update(kwargs.get("initial", {}))
        kwargs["initial"] = data
        super().__init__(*args, **kwargs)
        self.user = user

    @transaction.atomic
    def save(self):
        data = self.cleaned_data

        user = self.user
        user.first_name = data["first_name"].strip()
        user.last_name = data["last_name"].strip()
        user.save()

        profile = AttendeeProfile.objects.getOrCreateForUser(user)
        profile.phone = data["phone"]
        profile.birthday = data["birthday"]
        profile.job_title = data["job_title"]
        profile.company = data["company"]
        profile.company_homepage = data["company_homepage"]
        profile.save()
        profile.setBio(data["bio"])

        try:
            speaker = user.speaker

        except Speaker.DoesNotExist:
            speaker = Speaker.objects.create(user=user)

        conference = settings.CONFERNCE_CONFERENCE

        talk = Talk.objects.createFromTitle(
            title=data["title"],
            sub_title=data["sub_title"],
            prerequisites=data["prerequisites"],
            abstract_short=data["abstract_short"],
            abstract_extra=data["abstract_extra"],
            # TODO/FIXME(artcz): this should be a foreignkey to conference
            conference=conference,
            speaker=speaker,
            status="proposed",
            language=data["language"],
            domain=data["domain"],
            domain_level=data["domain_level"],
            level=data["level"],
            type=data["type"],
        )

        talk.save()
        talk.setAbstract(data["abstract"])

        if "tags" in data:
            valid_tags = validate_tags(data["tags"])
            talk.tags.set(*(valid_tags))

        return talk


urlpatterns = [
    url(
        r"^submit-proposal/step-1/$",
        submit_proposal_step1_talk_info,
        name="submit_proposal",
    ),
    url(
        r"^submit-proposal/step-2/(?P<talk_uuid>[\w-]+)/$",
        submit_proposal_step2_add_speakers,
        name="step2_add_speakers",
    ),
    url(
        r"^submit-proposal/step-3/(?P<talk_uuid>[\w-]+)/$",
        submit_proposal_step3_thanks,
        name="step3_thanks",
    ),
    url(
        r"^preview/(?P<talk_slug>[\w-]+)/$",
        preview_proposal,
        name="preview",
    ),
    url(
        r"^program-wg/download-all-talks/$",
        program_wg_download_all_talks_for_current_conference,
        name="program_wg_download_all_talks",
    ),
]
