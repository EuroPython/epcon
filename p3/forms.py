# -*- coding: UTF-8 -*-
from django import forms
from django.utils.translation import ugettext as _

from conference.forms import SubmissionForm
from conference.models import Ticket

from p3 import models

class P3SubmissionForm(SubmissionForm):
    mobile = forms.CharField(
        help_text=_('Enter a phone number where we can contact you in case of administrative issues.<br />Use the international format, eg: +39-055-123456'),
        max_length=20,
        required=True,)
    duration = forms.TypedChoiceField(
        label=_('Suggested duration'),
        help_text=_('This is the <b>net duration</b> of the talk, excluding Q&A'),
        choices=((45, '30 minutes'), (60, '45 minutes'), (90, '70 minutes')),
        coerce=int,
        initial=60,)

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            instance = kwargs['instance']
            data = {
                'mobile': instance.user.assopy_user.billing()['phone'],
            }
            data.update(kwargs.get('initial', {}))
            kwargs['initial'] = data
        super(P3SubmissionForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        talk = super(P3SubmissionForm, self).save(*args, **kwargs)
        instance = kwargs.get('instance') or self.instance
        data = self.cleaned_data
        instance.user.assopy_user.setBilling(phone=data['mobile'])
        return talk


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
