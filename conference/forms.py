# -*- coding: UTF-8 -*-
from django import forms
from django.db import transaction
from conference import models
from conference import settings
from django.utils.translation import ugettext as _

class SubmissionForm(forms.Form):
    first_name = forms.CharField(
        label=_('First name'),
        max_length=30,)
    last_name = forms.CharField(
        label=_('Last name'),
        max_length=30,)
    activity = forms.CharField(
        label=_('Job title'),
        help_text=_('eg: student, developer, CTO, js ninja, BDFL'),
        max_length=50,
        required=False,)
    activity_homepage = forms.URLField(label=_('Personal homepage'), required=False)
    company = forms.CharField(label=_('Your company'), max_length=50, required=False)
    company_homepage = forms.URLField(label=_('Company homepage'), required=False)
    industry = forms.TypedChoiceField(choices=models.SPEAKER_INDUSTRY, required=False)
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=forms.Textarea(),)
    previous_experience = forms.CharField(
        label=_('Previous experience'),
        help_text=_('List yout previous experiences'),
        widget=forms.Textarea(),
        required=False,)
    last_year_talks = forms.IntegerField(
        label=_('Last year talks'),
        help_text=_('How many talks you have held during the last year?'),
        min_value=0,
        required=False,)
    max_audience = forms.IntegerField(
        label=_('Maximum audience'),
        help_text=_('Specify the size of your biggest audience'),
        min_value=0,
        required=False,)

    title = forms.CharField(label=_('Talk title'), max_length=100, widget=forms.TextInput(attrs={'size': 40}))
    training = forms.BooleanField(
        label=_('Training'),
        help_text=_('Check if you are willing to also deliver a 4-hours hands-on training on this subject.<br />See the Call for paper for details.'),
        required=False,)
    type = forms.TypedChoiceField(
        label=_('Talk Type'),
        help_text=_('Talk Type description'),
        choices=models.TALK_TYPE,
        initial='s',
        required=True,)
    duration = forms.TypedChoiceField(
        label=_('Suggested duration'),
        help_text=_('This is the <b>net duration</b> of the talk, excluding Q&A'),
        choices=models.TALK_DURATION,
        coerce=int,
        initial='30',)
    language = forms.TypedChoiceField(
        help_text=_('Select Italian only if you are not comfortable in speaking English.'),
        choices=models.TALK_LANGUAGES,
        initial='en',)
    level = forms.TypedChoiceField(label=_('Audience level'), choices=models.TALK_LEVEL, initial='beginner')
    slides = forms.FileField(required=False,)
    abstract = forms.CharField(
        max_length=5000,
        label=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'),
        widget=forms.Textarea(),)
    promo_video = forms.URLField(
        label=_('Promo video'),
        help_text=_('Promo video description'),
        required=False,
    )

    def __init__(self, user, *args, **kwargs):
        try:
            speaker = user.speaker
        except models.Speaker.DoesNotExist:
            speaker = None
        data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        if speaker:
            data.update({
                'activity': speaker.activity,
                'activity_homepage': speaker.activity_homepage,
                'company': speaker.company,
                'company_homepage': speaker.company_homepage,
                'industry': speaker.industry,
                'bio': getattr(speaker.getBio(), 'body', ''),
                'previous_experience': speaker.previous_experience,
                'last_year_talks': speaker.last_year_talks,
                'max_audience': speaker.max_audience,
            })
        data.update(kwargs.get('initial', {}))
        kwargs['initial'] = data
        super(SubmissionForm, self).__init__(*args, **kwargs)
        self.user = user

    def clean_max_audience(self):
        try:
            data = int(self.cleaned_data['max_audience'])
        except:
            data = 0
        return data

    def clean_last_year_talks(self):
        try:
            data = int(self.cleaned_data['last_year_talks'])
        except:
            data = 0
        return data

    @transaction.commit_on_success
    def save(self):
        data = self.cleaned_data
        user = self.user
        user.first_name = data['first_name'].strip()
        user.last_name = data['last_name'].strip()
        user.save()

        name = '%s %s' % (data['first_name'], data['last_name'])
        try:
            speaker = user.speaker
        except models.Speaker.DoesNotExist:
            speaker = models.Speaker.objects.createFromName(name, user)
        else:
            speaker.name = name

        speaker.activity = data['activity']
        speaker.activity_homepage = data['activity_homepage']
        speaker.company = data['company']
        speaker.company_homepage = data['company_homepage']
        speaker.industry = data['industry']
        speaker.previous_experience = data['previous_experience']
        speaker.last_year_talks = data['last_year_talks']
        speaker.max_audience = data['max_audience']
        speaker.save()
        speaker.setBio(data['bio'])
        talk = models.Talk.objects.createFromTitle(
            title=data['title'], conference=settings.CONFERENCE, speaker=speaker,
            status='proposed', duration=data['duration'], language=data['language'],
            level=data['level'], training_available=data['training'],
        )
        talk.type = data['type']
        talk.promo_video_url = data['promo_video']
        if data['slides']:
            talk.slides = data['slides']
        talk.save()
        talk.setAbstract(data['abstract'])

        return talk

class SpeakerForm(forms.Form):
    activity = forms.CharField(
        label=_('Job title'),
        help_text=_('eg: student, developer, CTO, js ninja, BDFL'),
        max_length=50,
        required=False,)
    activity_homepage = forms.URLField(label=_('Personal homepage'), required=False)
    company = forms.CharField(label=_('Your company'), max_length=50, required=False)
    company_homepage = forms.URLField(label=_('Company homepage'), required=False)
    industry = forms.CharField(max_length=50, required=False)
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=forms.Textarea(),)
    ad_hoc_description = forms.CharField(label=_('Presentation'), required=False)

class TalkForm(forms.Form):
    title = forms.CharField(label=_('Talk title'), max_length=100, widget=forms.TextInput(attrs={'size': 40}))
    training = forms.BooleanField(
        label=_('Training'),
        help_text=_('Check if you are willing to also deliver a 4-hours hands-on training on this subject.<br />See the Call for paper for details.'),
        required=False,)
    duration = forms.TypedChoiceField(
        label=_('Suggested duration'),
        help_text=_('This is the <b>net duration</b> of the talk, excluding Q&A'),
        choices=models.TALK_DURATION,
        coerce=int,
        initial='30',)
    type = forms.TypedChoiceField(
        label=_('Talk Type'),
        choices=models.TALK_TYPE,
        initial='s',
        required=True,)
    language = forms.TypedChoiceField(
        help_text=_('Select Italian only if you are not comfortable in speaking English.'),
        choices=models.TALK_LANGUAGES,
        initial='en',)
    level = forms.TypedChoiceField(label=_('Audience level'), choices=models.TALK_LEVEL, initial='beginner')
    slides = forms.FileField(required=False)
    abstract = forms.CharField(
        label=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'),
        widget=forms.Textarea(),)
    promo_video = forms.URLField(
        label=_('Promo video'),
        help_text=_('Promo video description'),
        required=False,
    )

    def __init__(self, instance=None, *args, **kwargs):
        if instance:
            data = {
                'title': instance.title,
                'training': instance.training_available,
                'duration': instance.duration,
                'language': instance.language,
                'level': instance.level,
                'abstract': getattr(instance.getAbstract(), 'body', ''),
            }
            data.update(kwargs.get('initial', {}))
            kwargs['initial'] = data
        super(TalkForm, self).__init__(*args, **kwargs)
        self.instance = instance

    @transaction.commit_on_success
    def save(self, instance=None, speaker=None):
        if instance is None:
            instance = self.instance
        data = self.cleaned_data
        if instance is None:
            assert speaker is not None
            instance = models.Talk.objects.createFromTitle(
                title=data['title'], conference=settings.CONFERENCE, speaker=speaker,
                status='proposed', duration=data['duration'], language=data['language'],
                level=data['level'], training_available=data['training'],
            )
        else:
            instance.title = data['title']
            instance.duration = data['duration']
            instance.language = data['language']
            instance.level = data['level']
            instance.training_available = data['training']

        instance.type = data['type']
        instance.promo_video_url = data['promo_video']
        if data['slides']:
            instance.slides = data['slides']
        instance.save()
        instance.setAbstract(data['abstract'])

        return instance

from tagging.models import TaggedItem
from tagging.utils import parse_tag_input

class EventForm(forms.ModelForm):
    class Meta:
        model = models.Event
        exclude = ('schedule',)

    def __init__(self, *args, **kwargs):
        i = kwargs.get('instance', None)
        if not i:
            self.schedule = kwargs.pop('schedule')
        else:
            self.schedule = i.schedule
        super(EventForm, self).__init__(*args, **kwargs)
        self.fields['talk'].queryset = models.Talk.objects\
            .filter(conference=self.schedule.conference)

    def clean_track(self):
        data = self.cleaned_data
        tracks = set(parse_tag_input(data['track']))
        allowed = set(t.track for t in self.schedule.track_set.all()) | set(('special', 'break', 'teaser'))
        if tracks - allowed:
            raise forms.ValidationError('invalid tracks names: "%s"' % ' '.join(tracks - allowed))
        return data['track']
        
    def clean(self):
        data = super(EventForm, self).clean()
        if not data['talk'] and not data['custom']:
            raise forms.ValidationError('set the talk or the custom text')

        tracks = set(parse_tag_input(data['track']))
        if 'special' in tracks or 'break' in tracks:
            tracks |= set(t.track for t in self.schedule.track_set.all())
        tracks -= set(('teaser',))
        for t in tracks:
            conflicts = set(TaggedItem.objects.get_by_model(models.Event.objects.filter(schedule=self.schedule, start_time=data['start_time']), t))
            if self.instance:
                conflicts = conflicts - set((self.instance,))
            if conflicts:
                raise forms.ValidationError('conflicts on "%s"' % data['start_time'])

        return data
