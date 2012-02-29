# -*- coding: UTF-8 -*-
from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.translation import ugettext as _

import conference.forms as cforms 
import conference.models as cmodels

from p3 import models

import datetime

class P3SubmissionForm(cforms.SubmissionForm):
    duration = forms.TypedChoiceField(
        label=_('Duration'),
        help_text=_('This is the <b>suggested net duration</b> of the talk, excluding Q&A'),
        choices=((45, '30 minutes'), (60, '45 minutes'), (90, '70 minutes'), (240, '4 hours')),
        coerce=int,
        initial=60,
        required=False,
    )
    first_time = forms.BooleanField(
        label=_('I\'m a first-time speaker'),
        help_text=_('We are planning a special program to help first time speaker, check this if you\'d like to join'),
        required=False,
    )
    type = forms.TypedChoiceField(
        label=_('Talk Type'),
        help_text='Choose between a standard talk, a 4-hours in-depth training or a poster session',
        choices=(('s', 'Standard talk'), ('t', 'Training'), ('p', 'Poster session'),),
        initial='s',
        required=True,
        widget=forms.RadioSelect(renderer=cforms.PseudoRadioRenderer),
    )
    personal_agreement = forms.BooleanField(
        label=_('I agree to let you publish my data (excluding birth date and phone number).'),
        help_text=_('This speaker profile will be publicly accesible if one of your talks is accepted. Your mobile phone and date of birth will <strong>never</strong> be published'),
    )
    slides_agreement = forms.BooleanField(
        label=_('I agree to release all the talk material after the event.'),
        help_text=_('If the talk is accepted, speakers a required to timely release all the talk material (including slides) for publishing on this web site.'),
    )
    video_agreement = forms.BooleanField(
        label=_('I agree to let the organization record my talk and publish the video.'),
    )
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=cforms.MarkEditWidget,)
    abstract = forms.CharField(
        max_length=5000,
        label=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'),
        widget=cforms.MarkEditWidget,)

    language = forms.TypedChoiceField(
        help_text=_('Select Italian only if you are not comfortable in speaking English.'),
        choices=cmodels.TALK_LANGUAGES,
        initial='en', required=False)

    def __init__(self, user, *args, **kwargs):
        data = {
            'mobile': user.assopy_user.phone,
            'birthday': user.assopy_user.birthday,
            'activity_homepage': user.assopy_user.www,
        }
        data.update(kwargs.get('initial', {}))
        kwargs['initial'] = data
        super(P3SubmissionForm, self).__init__(user, *args, **kwargs)

    def clean(self):
        data = super(P3SubmissionForm, self).clean()
        if data['type'] == 't':
            data['duration'] = 240

        if not data.get('duration'):
            data['duration'] = 45

        if not data.get('language') or data['type'] != 's':
            data['language'] = 'en'

        return data

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        talk = super(P3SubmissionForm, self).save(*args, **kwargs)

        speaker = self.user.speaker
        try:
            p3s = speaker.p3_speaker
        except models.SpeakerConference.DoesNotExist:
            p3s = models.SpeakerConference(speaker=speaker)
            
        data = self.cleaned_data

        p3s.first_time = data['first_time']
        p3s.save()

        return talk

class P3SubmissionAdditionalForm(cforms.TalkForm):
    duration = forms.TypedChoiceField(
        label=_('Duration'),
        help_text=_('This is the <b>suggested net duration</b> of the talk, excluding Q&A'),
        choices=((45, '30 minutes'), (60, '45 minutes'), (90, '70 minutes'), (240, '4 hours')),
        coerce=int,
        initial=60,
        required=False,
    )
    slides_agreement = forms.BooleanField(
        label=_('I agree to release all the talk material after the event.'),
        help_text=_('If the talk is accepted, speakers a required to timely release all the talk material (including slides) for publishing on this web site.'),
    )
    video_agreement = forms.BooleanField(
        label=_('I agree to let the organization record my talk and publish the video.'),
    )
    type = forms.TypedChoiceField(
        label=_('Talk Type'),
        help_text='Choose between a standard talk, a 4-hours in-depth training or a poster session',
        choices=(('s', 'Standard talk'), ('t', 'Training'), ('p', 'Poster session'),),
        initial='s',
        required=True,
        widget=forms.RadioSelect(renderer=cforms.PseudoRadioRenderer),
    )
    abstract = forms.CharField(
        max_length=5000,
        label=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'),
        widget=cforms.MarkEditWidget,)

    language = forms.TypedChoiceField(
        help_text=_('Select Italian only if you are not comfortable in speaking English.'),
        choices=cmodels.TALK_LANGUAGES,
        initial='en', required=False)

    def clean(self):
        data = super(P3SubmissionAdditionalForm, self).clean()
        if data['type'] == 't':
            data['duration'] = 240

        if not data.get('duration'):
            data['duration'] = 45

        if not data.get('language') or data['type'] != 's':
            data['language'] = 'en'
        return data

class P3TalkForm(cforms.TalkForm):
    duration = forms.TypedChoiceField(
        label=_('Duration'),
        help_text=_('This is the <b>suggested net duration</b> of the talk, excluding Q&A'),
        choices=((45, '30 minutes'), (60, '45 minutes'), (90, '70 minutes'), (240, '4 hours')),
        coerce=int,
        initial=60,
        required=False,
    )
    type = forms.TypedChoiceField(
        label=_('Talk Type'),
        help_text='Choose between a standard talk, a 4-hours in-depth training or a poster session',
        choices=(('s', 'Standard talk'), ('t', 'Training'), ('p', 'Poster session'),),
        initial='s',
        required=True,
        widget=forms.RadioSelect,
    )
    abstract = forms.CharField(
        max_length=5000,
        label=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'),
        widget=cforms.MarkEditWidget,)

    def clean(self):
        data = super(P3TalkForm, self).clean()
        if data['type'] == 't':
            data['duration'] = 240

        if not data.get('duration'):
            data['duration'] = 45

        if not data.get('language') or data['type'] != 's':
            data['language'] = 'en'
        return data

class P3SpeakerForm(cforms.SpeakerForm):
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=cforms.MarkEditWidget,)

class FormTicket(forms.ModelForm):
    ticket_name = forms.CharField(max_length=60, required=False, help_text='name of the attendee')
    days = forms.MultipleChoiceField(choices=tuple(), widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = models.TicketConference
        exclude = ('ticket',)
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
            data = map(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'), filter(None, raw))
        except Exception, e:
            raise forms.ValidationError('formato data non valido')
        conf = cmodels.Conference.objects.current()
        days = []
        for x in data:
            if conf.conference_start <= x.date() <= conf.conference_end:
                days.append(x.strftime('%Y-%m-%d'))
            else:
                raise forms.ValidationError('data non valida')
        if self.single_day:
            return days[0] if days else ''
        else:
            return ','.join(days)

    def clean(self):
        data = self.cleaned_data
        if not data.get('ticket_name') and not data.get('assigned_to'):
            forms.ValidationError('invalid name')
        return data

class FormTicketPartner(forms.ModelForm):
    name = forms.CharField(max_length=60, required=False, help_text='Real name of the person that will attend this specific event.')
    class Meta:
        model = cmodels.Ticket
        fields = ('name',)

class FormTicketSIM(forms.ModelForm):
    ticket_name = forms.CharField(max_length=60, help_text='The SIM owner')
    class Meta:
        model = models.TicketSIM
        exclude = ('ticket',)
        fields = ('ticket_name', 'sim_type', 'plan_type', 'document',)

class FormSprint(forms.ModelForm):
    class Meta:
        model = models.Sprint
        exclude = ('user', 'conference',)

class P3ProfileForm(cforms.ProfileForm):
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=cforms.MarkEditWidget,
        required=False,)
    interests = cforms.TagField(widget=cforms.TagWidget, required=False)
    twitter = forms.CharField(max_length=80, required=False)
    visibility = forms.ChoiceField(choices=cmodels.ATTENDEEPROFILE_VISIBILITY, widget=forms.RadioSelect, required=False)

    image_gravatar= forms.BooleanField(required=False, widget=forms.HiddenInput)
    image_url = forms.URLField(required=False)
    image = forms.FileField(required=False, widget=forms.FileInput)

    def __init__(self, *args, **kw):
        i = kw.get('instance')
        if i:
            try:
                p3p = i.p3_profile
            except models.P3Profile.DoesNotExist:
                pass
            else:
                initial = kw.get('initial', {})
                initial.update({
                    'interests': p3p.interests.all(),
                    'twitter': p3p.twitter,
                    'image_gravatar': p3p.image_gravatar,
                    'image_url': p3p.image_url,
                })
                kw['initial'] = initial
        super(P3ProfileForm, self).__init__(*args, **kw)

    def clean(self):
        data = self.cleaned_data
        data['visibility'] = data.get('visibility', 'x')
        return data

    def clean_twitter(self):
        data = self.cleaned_data.get('twitter', '')
        if data.startswith('@'):
            data = data[1:]
        return data
    
    def save(self, commit=True):
        assert commit, "Aggiornare P3ProfileForm per funzionare con commit=False"
        profile = super(P3ProfileForm, self).save(commit=commit)
        try:
            p3p = profile.p3_profile
        except models.P3Profile.DoesNotExist:
            p3p = models.P3Profile(profile=profile)
            p3p.save()
        return profile


class P3ProfilePublicDataForm(P3ProfileForm):
    class Meta:
        model = cmodels.AttendeeProfile
        fields = ('personal_homepage', 'interests', 'twitter', 'company', 'company_homepage', 'job_title', 'location',)

    def clean_bio(self):
        return getattr(self.instance.getBio(), 'body', '')

    def save(self, commit=True):
        profile = super(P3ProfilePublicDataForm, self).save(commit)
        p3p = profile.p3_profile
        data = self.cleaned_data
        p3p.twitter = data.get('twitter', '')
        p3p.interests.set(*data.get('interests', ''))
        return profile

class P3ProfileBioForm(P3ProfileForm):
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=cforms.MarkEditWidget,
        required=False,)
    class Meta:
        model = cmodels.AttendeeProfile
        fields = ()
    def save(self, commit=True):
        profile = super(P3ProfileBioForm, self).save(commit)
        data = self.cleaned_data
        profile.setBio(data.get('bio', ''))
        return profile

class P3ProfileVisibilityForm(P3ProfileForm):
    visibility = forms.ChoiceField(choices=cmodels.ATTENDEEPROFILE_VISIBILITY, widget=forms.RadioSelect)
    class Meta:
        model = cmodels.AttendeeProfile
        fields = ('visibility',)

    def clean_bio(self):
        return getattr(self.instance.getBio(), 'body', '')

class P3ProfilePictureForm(P3ProfileForm):
    opt = forms.ChoiceField(choices=(
            ('x', 'no picture'),
            ('g', 'use gravatar'),
            ('u', 'use url'),
            ('f', 'upload file'),
        ), required=False)
    image_gravatar= forms.BooleanField(required=False, widget=forms.HiddenInput)
    image_url = forms.URLField(required=False)
    image = forms.FileField(required=False, widget=forms.FileInput)

    class Meta:
        model = cmodels.AttendeeProfile
        fields = ('image',)

    def clean_bio(self):
        return getattr(self.instance.getBio(), 'body', '')

    def clean(self):
        data = self.cleaned_data
        opt = data.get('opt', 'x')
        if opt == 'x':
            data['image'] = False
            data['image_gravatar'] = False
            data['image_url'] = ''
        elif opt == 'g':
            data['image'] = False
            data['image_gravatar'] = True
            data['image_url'] = ''
        elif opt == 'u':
            data['image'] = False
            data['image_gravatar'] = False
        elif opt == 'f':
            data['image_gravatar'] = False
            data['image_url'] = ''
        return data

    def save(self, commit=True):
        profile = super(P3ProfilePictureForm, self).save(commit)
        p3p = profile.p3_profile
        data = self.cleaned_data
        p3p.image_gravatar = data.get('image_gravatar', False)
        p3p.image_url = data.get('image_url', '')
        p3p.save()
        return profile

class P3ProfilePersonalDataForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    phone = forms.CharField(
        help_text=_('We require a mobile number for all speakers for important last minutes contacts.<br />Use the international format, eg: +39-055-123456.<br />This number will <strong>never</strong> be published.'),
        max_length=30,
        required=False,
    )
    birthday = forms.DateField(
        label=_('Date of birth'),
        help_text=_('We require date of birth for speakers to accomodate for Italian laws regarding minors.<br />Format: YYYY-MM-DD<br />This date will <strong>never</strong> be published.'),
        input_formats=('%Y-%m-%d',),
        widget=forms.DateInput(attrs={'size': 10, 'maxlength': 10}),
        required=False,
    )

    class Meta:
        model = cmodels.AttendeeProfile
        fields = ('phone', 'birthday')

    def clean_phone(self):
        value = self.cleaned_data.get('phone', '')
        try:
            self.instance.user.speaker
        except (AttributeError, User.DoesNotExist, cmodels.Speaker.DoesNotExist):
            pass
        else:
            if not value:
                raise forms.ValidationError('This field is required for a speaker')
        return value

    def clean_birthday(self):
        value = self.cleaned_data.get('birthday', '')
        try:
            self.instance.user.speaker
        except (AttributeError, User.DoesNotExist, cmodels.Speaker.DoesNotExist):
            pass
        else:
            if not value:
                raise forms.ValidationError('This field is required for a speaker')
        return value

class P3ProfileEmailContactForm(forms.Form):
    email = forms.EmailField(label="Enter new email")
