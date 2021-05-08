from django import forms
from django.template.defaultfilters import slugify

from taggit.forms import TagField
from taggit_labels.widgets import LabelWidget

from conference.forms import TalkBaseForm
from conference.models import (Conference, ConferenceTag, Talk, TALK_TYPE,
    CFP_TALK_TYPE, AttendeeProfile)

from phonenumber_field.formfields import PhoneNumberField


class TalkUpdateForm(forms.ModelForm):
    # Talk tags
    tags = TagField(required=True, widget=LabelWidget(model=ConferenceTag))

    title = TalkBaseForm.base_fields["title"]
    sub_title = TalkBaseForm.base_fields["sub_title"]
    abstract = TalkBaseForm.base_fields["abstract"]
    abstract_short = TalkBaseForm.base_fields["abstract_short"]
    prerequisites = TalkBaseForm.base_fields["prerequisites"]
    level = TalkBaseForm.base_fields["level"]
    domain_level = TalkBaseForm.base_fields["domain_level"]
    if 'availability' in TalkBaseForm.base_fields:
        availability = TalkBaseForm.base_fields["availability"]

    class Meta:
        model = Talk
        fields = [
            "title",
            "sub_title",
            "abstract",
            "abstract_short",
            "prerequisites",
            "level",
            "domain_level",
            "tags",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if kwargs.get("instance"):
            self.fields["abstract"].initial = kwargs["instance"].getAbstract().body
            self.fields['availability'].initial = kwargs['instance'].get_availability()

    def save(self, user):
        """
        We don't support commit=False on this form, because .setAbstract
        requires an object saved in db.
        """
        talk = super().save(commit=False)
        talk.created_by = user
        talk.slug = f"{talk.uuid}-{slugify(talk.title)}"
        talk.conference = Conference.objects.current().code
        talk.set_availability(self.cleaned_data['availability'])
        talk.save()
        talk.setAbstract(self.cleaned_data["abstract"])

        if "tags" in self.cleaned_data:
            talk.tags.set(*validate_tags(self.cleaned_data["tags"]))

        return talk

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
    i_accept_speaker_release  = TalkBaseForm.base_fields[
        'i_accept_speaker_release'
    ]


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

class TalkSlidesForm(forms.ModelForm):
    class Meta:
        model = Talk
        fields = [
            "slides", "slides_url", "repository_url"
        ]


class ProposalForm(TalkUpdateForm):
    type = forms.ChoiceField(label="Type", required=True, choices=CFP_TALK_TYPE)

    abstract_extra = TalkBaseForm.base_fields["abstract_extra"]

    class Meta:
        model = Talk
        fields = TalkUpdateForm.Meta.fields + ["type", "abstract_extra"]


def validate_tags(tags):
    """
    Returns only tags that are already present in the database
    and limits the results to 5
    """
    valid_tags = ConferenceTag.objects.filter(name__in=tags).values_list(
        "name", flat=True
    )

    tags_limited = valid_tags[:5]

    return tags_limited
