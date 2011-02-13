# -*- coding: UTF-8 -*-
from django import forms
from conference.models import Ticket
import models

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
