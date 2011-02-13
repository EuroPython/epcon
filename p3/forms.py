# -*- coding: UTF-8 -*-
from django import forms
import models

class FormAttendee(forms.ModelForm):
    attendee_name = forms.CharField(max_length=60, required=False)

    class Meta:
        model = models.AttendeeProfile
        exclude = ('attendee',)
        widgets = {
            'assigned_to': forms.HiddenInput(),
        }
