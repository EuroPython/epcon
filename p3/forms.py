# -*- coding: UTF-8 -*-
from django import forms
import models

class FormTicket(forms.ModelForm):
    ticket_name = forms.CharField(max_length=60, required=False)

    class Meta:
        model = models.TicketConference
        exclude = ('ticket',)
        widgets = {
            'assigned_to': forms.HiddenInput(),
        }
