# -*- coding: UTF-8 -*-
from django import forms
from django.db import transaction
from django.utils.translation import ugettext as _

from conference.forms import SubmissionForm, TalkForm
from conference.models import Conference, Ticket

from p3 import models

import datetime

class P3SubmissionForm(SubmissionForm):
    mobile = forms.CharField(
        help_text=_('We require a mobile number for all speakers for important last minutes contacts.<br />Use the international format, eg: +39-055-123456.<br />This number will <strong>never</strong> be published.'),
        max_length=30,
        required=True,)
    birthday = forms.DateField(
        label=_('Date of birth'),
        help_text=_('We require date of birth for speakers to accomodate for Italian laws regarding minors.<br />Format: YYYY-MM-DD<br />This date will <strong>never</strong> be published.'),
        input_formats=('%Y-%m-%d',),
    )
    duration = forms.TypedChoiceField(
        label=_('Suggested duration'),
        help_text=_('This is the <b>net duration</b> of the talk, excluding Q&A'),
        choices=((45, '30 minutes'), (60, '45 minutes'), (90, '70 minutes')),
        coerce=int,
        initial=60,)
    # per ep non c'è il tipo di talk
    type = forms.TypedChoiceField(required=False)
    personal_agreement = forms.BooleanField(
        label=_('I agree to let you publish my data on the web site.'),
        help_text=_('This speaker profile will be publicly accesible if one of your talks is accepted. Your mobile phone and date of birth will <strong>never</strong> be published'),
    )
    slides_agreement = forms.BooleanField(
        label=_('I agree to release all the talk material after the event.'),
        help_text=_('If the talk is accepted, speakers a required to timely release all the talk material (including slides) for publishing on this web site.'),
    )
    video_agreement = forms.BooleanField(
        label=_('I agree to let the organization record my talk and publish the video.'),
    )

    def __init__(self, user, *args, **kwargs):
        data = {
            'mobile': user.assopy_user.phone,
            'birthday': user.assopy_user.birthday,
            'activity_homepage': user.assopy_user.www,
        }
        data.update(kwargs.get('initial', {}))
        kwargs['initial'] = data
        super(P3SubmissionForm, self).__init__(user, *args, **kwargs)

    def clean_type(self):
        return 's'

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        talk = super(P3SubmissionForm, self).save(*args, **kwargs)

        auser = self.user.assopy_user
        speaker = self.user.speaker
        data = self.cleaned_data

        auser.phone = data['mobile']
        auser.birthday = data['birthday']
        auser.www = data['activity_homepage']
        auser.save()

        return talk

class P3SubmissionAdditionalForm(TalkForm):
    duration = forms.TypedChoiceField(
        label=_('Suggested duration'),
        help_text=_('This is the <b>net duration</b> of the talk, excluding Q&A'),
        choices=((45, '30 minutes'), (60, '45 minutes'), (90, '70 minutes')),
        coerce=int,
        initial=60,)
    slides_agreement = forms.BooleanField(
        label=_('I agree to release all the talk material after the event.'),
        help_text=_('If the talk is accepted, speakers a required to timely release all the talk material (including slides) for publishing on this web site.'),
    )
    video_agreement = forms.BooleanField(
        label=_('I agree to let the organization record my talk and publish the video.'),
    )
    type = forms.TypedChoiceField(required=False)

    def clean_type(self):
        return 's'

class P3TalkForm(TalkForm):
    duration = forms.TypedChoiceField(
        label=_('Suggested duration'),
        help_text=_('This is the <b>net duration</b> of the talk, excluding Q&A'),
        choices=((45, '30 minutes'), (60, '45 minutes'), (90, '70 minutes'), (240, '240 minutes')),
        coerce=int,
        initial=60,)
    type = forms.TypedChoiceField(required=False)

    def clean_type(self):
        return 's'

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
        conf = Conference.objects.current()
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
        conf = Conference.objects.current()
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
        model = Ticket
        fields = ('name',)

class FormTicketSIM(forms.ModelForm):
    ticket_name = forms.CharField(max_length=60, help_text='The SIM owner')
    class Meta:
        model = models.TicketSIM
        exclude = ('ticket',)
        fields = ('ticket_name', 'sim_type', 'plan_type', 'document',)
