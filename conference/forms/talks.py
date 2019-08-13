from django import forms
from django.template.defaultfilters import slugify

from taggit.forms import TagField
from taggit_labels.widgets import LabelWidget

from conference.forms import TalkBaseForm
from conference.models import Conference, ConferenceTag, Talk, TALK_TYPE


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

    def save(self, user):
        """
        We don't support commit=False on this form, because .setAbstract
        requires an object saved in db.
        """
        talk = super().save(commit=False)
        talk.created_by = user
        talk.slug = f"{talk.uuid}-{slugify(talk.title)}"
        talk.conference = Conference.objects.current().code
        talk.save()
        talk.setAbstract(self.cleaned_data["abstract"])

        if "tags" in self.cleaned_data:
            talk.tags.set(*validate_tags(self.cleaned_data["tags"]))

        return talk


class TalkSlidesForm(forms.ModelForm):
    class Meta:
        model = Talk
        fields = [
            "slides", "slides_url", "repository_url"
        ]


class ProposalForm(TalkUpdateForm):
    type = forms.ChoiceField(label="Type", required=True, choices=TALK_TYPE)

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
