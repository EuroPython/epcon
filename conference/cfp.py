from django import forms
from django.conf import settings
from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.template.response import TemplateResponse

from conference.forms import TalkBaseForm, validate_tags
from conference.models import AttendeeProfile, Speaker, Talk, TALK_TYPE


@login_required
def submit_proposal(request):
    """
    Main submit_proposal view for ep2019+
    """

    proposal_form = ProposalSubmissionForm(request.user)

    return TemplateResponse(request, "ep19/bs/cfp/submit_proposal.html", {
        "proposal_form": proposal_form,
    })


class ProposalSubmissionForm(forms.Form):
    """
    Submission Form for the first paper, it will contain the fields
    which populates the user profile and the data of the talk,
    only essential data is required.
    """

    # Speaker details
    first_name = forms.CharField(label="First name", max_length=30)
    last_name = forms.CharField(label="Last name", max_length=30)
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
    phone = forms.CharField(
        help_text=(
            "We require a mobile number for all speakers for important "
            "last minutes contacts.<br />Use the international format, "
            "eg: +39-055-123456.<br />"
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
    url("^submit-proposal/$", submit_proposal, name="submit_proposal")
]
