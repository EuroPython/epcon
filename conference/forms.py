# -*- coding: UTF-8 -*-
from django import forms
from conference import models
from conference import settings
from django.utils.translation import ugettext as _

class SubmissionForm(forms.Form):
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

    title = forms.CharField(label=_('Talk title'), max_length=100, widget=forms.TextInput(attrs={'size': 40}))
    training = forms.BooleanField(
        label=_('Training'),
        help_text=_('Check if you are willing to also deliver a 4-hours hands-on training on this subject.<br />See te Call for paper for details.'),
        required=False,)
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
    slides = forms.FileField(required=False)
    abstract = forms.CharField(
        label=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'),
        widget=forms.Textarea(),)

    def __init__(self, instance=None, *args, **kwargs):
        if instance:
            data = {
                'activity': instance.activity,
                'activity_homepage': instance.activity_homepage,
                'company': instance.company,
                'company_homepage': instance.company_homepage,
                'industry': instance.industry,
                'bio': getattr(instance.getBio(), 'body', ''),
            }
            data.update(kwargs.get('initial', {}))
            kwargs['initial'] = data
        super(SubmissionForm, self).__init__(*args, **kwargs)
        self.instance = instance

    def save(self, instance=None):
        if instance is None:
            instance = self.instance
        data = self.cleaned_data
        instance.activity = data['activity']
        instance.activity_homepage = data['activity_homepage']
        instance.company = data['company']
        instance.company_homepage = data['company_homepage']
        instance.industry = data['industry']
        instance.save()
        instance.setBio(data['bio'])
        talk = models.Talk.objects.createFromTitle(
            title=data['title'], conference=settings.CONFERENCE, speaker=instance,
            status='proposed', duration=data['duration'], language=data['language'],
            level=data['level'], training_available=data['training'],
        )
        if data['slides']:
            talk.slides = data['slides']
            talk.save()
        talk.setAbstract(data['abstract'])

        return talk

class SpeakerForm(forms.Form):
    activity = forms.CharField(max_length=50, required=False)
    activity_homepage = forms.URLField(required=False)
    industry = forms.CharField(max_length=50, required=False)
    bio = forms.CharField(widget=forms.Textarea())

class TalkForm(forms.Form):
    title = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'size': 40}))
    duration = forms.TypedChoiceField(choices=models.TALK_DURATION, coerce=int, initial='30')
    language = forms.TypedChoiceField(choices=models.TALK_LANGUAGES, initial='en')
    slides = forms.FileField(required=False)
    abstract = forms.CharField(widget=forms.Textarea())
