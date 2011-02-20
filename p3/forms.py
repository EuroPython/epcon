# -*- coding: UTF-8 -*-
from django import forms
from django.utils.translation import ugettext as _

from conference.forms import SubmissionForm, TalkForm
from conference.models import Ticket

from p3 import models

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

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs and kwargs['instance']:
            instance = kwargs['instance']
            data = {
                'mobile': instance.user.assopy_user.phone,
                'birthday': instance.user.assopy_user.birthday,
            }
            data.update(kwargs.get('initial', {}))
            kwargs['initial'] = data
        super(P3SubmissionForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        talk = super(P3SubmissionForm, self).save(*args, **kwargs)
        instance = kwargs.get('instance') or self.instance
        data = self.cleaned_data
        instance.user.assopy_user.phone = data['mobile']
        instance.user.assopy_user.birthday = data['birthday']
        instance.user.assopy_user.save()
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

class P3TalkForm(TalkForm):
    duration = forms.TypedChoiceField(
        label=_('Suggested duration'),
        help_text=_('This is the <b>net duration</b> of the talk, excluding Q&A'),
        choices=((45, '30 minutes'), (60, '45 minutes'), (90, '70 minutes')),
        coerce=int,
        initial=60,)

class FormTicket(forms.ModelForm):
    ticket_name = forms.CharField(max_length=60, required=False, help_text='name of the attendee')

    class Meta:
        model = models.TicketConference
        exclude = ('ticket',)
        widgets = {
            'assigned_to': forms.HiddenInput(),
        }

    def clean(self):
        data = self.cleaned_data
        if not data.get('ticket_name') and not data.get('assigned_to'):
            forms.ValidationError('invalid name')
        return data

class FormTicketPartner(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('name',)
