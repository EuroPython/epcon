import datetime

from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _

import conference.forms as cforms
import conference.models as cmodels

from p3 import dataaccess
from p3 import models

### Globals

## TODO: These forms are candidates for removal

class P3TalkFormMixin(object):
    def clean(self):
        data = super(P3TalkFormMixin, self).clean()

        # You can select the right duration now, so this is no longer
        # needed
        #if data['type'] in ('t', 'h'):
        #    data['duration'] = 240
        # Set default language
        if not data.get('language'):
            data['language'] = 'en'
        return data


## Normal CFP:
TALK_TYPE_FORM = list(cmodels.TALK_TYPE)

# Add a non-valid default choice for the talk type to force the user
# to select one
TALK_TYPE_FORM.insert(0, ("", "----------------"))

class P3SubmissionForm(P3TalkFormMixin, cforms.SubmissionForm):
    #first_time = forms.BooleanField(
    #    label=_('I\'m a first-time speaker'),
    #    help_text=_('This setting will be visible for the Program WG to use in their talk selection. The WG may contact you to ask you to participate in a first time speaker training session.'),
    #    required=False,
    #)
    type = forms.TypedChoiceField(
        label=_('Submission type'),
        help_text='Choose between a standard talk, an in-depth training, a poster session or an help desk session',
        choices=TALK_TYPE_FORM,
        required=True,
    )

    # Note: These three fields are *not* saved in the talk record,
    # they are just used to show the checkboxes when first submitting
    # a talk and required, so that no talk can be submitted without
    # checking them.
    personal_agreement = forms.BooleanField(
        label=_('I agree to let you publish my profile data (excluding birth date and phone number).'),
        help_text=_('The speaker profile will be publicly accessible if one of your talks is accepted. Your mobile phone and date of birth will <i>never</i> be published'),
    )
    slides_agreement = forms.BooleanField(
        label=_('I agree to upload my presentation material after the event to this web site.'),
        help_text=_('If the talk is accepted, speakers are encouraged to upload their talk slides to make them available to users of this web site.'),
    )
    video_agreement = forms.BooleanField(
        label=_('I agree to have my presentation recorded and have read, understood and agree to the <a href="/speaker-release-agreement/">EuroPython Speaker Release Agreement</a>'),
        help_text=_('We will be recording the conference talks and publish them on the EuroPython YouTube channel and archive.org.'),
    )

    domain = forms.ChoiceField(
        label=_('Domain / Track'),
        help_text=_('Select the domain / track suggestion for the talk. This will help us with the conference scheduling.'),
        choices=settings.CONFERENCE_TALK_DOMAIN,
        initial='',
        required=False)

    domain_level = forms.ChoiceField(
        label=_('Domain Expertise'),
        help_text=_('The domain expertise your audience should have to follow along (e.g. how much should one know about DevOps or Data Science already)'),
        choices=cmodels.TALK_LEVEL,
        initial=cmodels.TALK_LEVEL.beginner,
        required=False)

    def __init__(self, user, *args, **kwargs):
        data = {}
        data.update(kwargs.get('initial', {}))
        kwargs['initial'] = data
        super(P3SubmissionForm, self).__init__(user, *args, **kwargs)

    #@transaction.atomic
    def save(self, *args, **kwargs):
        talk = super(P3SubmissionForm, self).save(*args, **kwargs)

        speaker = self.user.speaker
        try:
            p3s = speaker.p3_speaker
        except models.SpeakerConference.DoesNotExist:
            p3s = models.SpeakerConference(speaker=speaker)

        data = self.cleaned_data

        p3s.first_time = data.get('first_time', False)
        p3s.save()

        # Set additional fields added in this form (compared to
        # cforms.SubmissionForm)
        models.P3Talk.objects.get_or_create(talk=talk)

        return talk


class P3TalkForm(P3TalkFormMixin, cforms.TalkForm):
    type = P3SubmissionForm.base_fields['type']

    class Meta(cforms.TalkForm.Meta):
        exclude = ('duration', 'qa_duration',)


class P3SpeakerForm(cforms.SpeakerForm):
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Short biography (one or two paragraphs). Do not paste your CV'),
        widget=forms.Textarea,)


class FormTicket(forms.ModelForm):
    ticket_name = forms.CharField(max_length=60, required=False, help_text='Name of the attendee')
    days = forms.MultipleChoiceField(label=_('Probable days of attendance'), choices=tuple(), widget=forms.CheckboxSelectMultiple, help_text=_('Please note: The above selection is just for helping the organizers with the catering estimates. It is not binding for you.'),required=False)

    class Meta:
        model = models.TicketConference
        exclude = ('ticket', 'badge_image',)
        widgets = {
            'assigned_to': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        single_day = kwargs.pop('single_day', False)
        if kwargs.get('instance'):
            data = {
                'days': kwargs['instance'].days.split(','),
            }
            data.update(kwargs.get('initial', {}))
            kwargs['initial'] = data
        if single_day:
            if 'initial' in kwargs and kwargs['initial'].get('days', []):
                kwargs['initial']['days'] = kwargs['initial']['days'][0]
        super(FormTicket, self).__init__(*args, **kwargs)
        self.single_day = single_day
        if single_day:
            self.fields['days'] = forms.ChoiceField(
                label=_('Days'), choices=tuple(), widget=forms.RadioSelect, required=False)

        days = []
        conf = cmodels.Conference.objects.current()
        d = conf.conference_start
        while d <= conf.conference_end:
            days.append((d.strftime('%Y-%m-%d'), d.strftime('%a, %d %b')))
            d = d + datetime.timedelta(days=1)
        self.fields['days'].choices = days

    def clean_days(self):
        raw = self.cleaned_data.get('days')
        if self.single_day:
            raw = [ raw ]
        try:
            data = [datetime.datetime.strptime(x, '%Y-%m-%d') for x in [_f for _f in raw if _f]]
        except Exception:
            raise forms.ValidationError('data format not valid')
        conf = cmodels.Conference.objects.current()
        days = []
        for x in data:
            if conf.conference_start <= x.date() <= conf.conference_end:
                days.append(x.strftime('%Y-%m-%d'))
            else:
                raise forms.ValidationError('data not valid')
        if self.single_day:
            return days[0] if days else ''
        else:
            return ','.join(days)

    def clean(self):
        data = self.cleaned_data
        if not data.get('ticket_name') and not data.get('assigned_to'):
            forms.ValidationError('invalid name')
        return data
