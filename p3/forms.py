# -*- coding: UTF-8 -*-
from django import forms
from conference.models import Ticket
import models

class FormTicket(forms.ModelForm):
    ticket_name = forms.CharField(max_length=60, required=True, help_text='name of the attendee')

    class Meta:
        model = models.TicketConference
        exclude = ('ticket',)
        widgets = {
            'assigned_to': forms.HiddenInput(),
        }

class FormTicketPartner(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('name',)
