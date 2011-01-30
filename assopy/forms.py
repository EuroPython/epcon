# -*- coding: UTF-8 -*-
from django import forms
from conference import models as cmodels

class Profile(forms.Form):
    firstname = forms.CharField(max_length=32)
    lastname = forms.CharField(max_length=32)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)
    www = forms.URLField(verify_exists=False, required=False)
    photo = forms.FileField(required=False)

class BillingData(forms.Form):
    card_name = forms.CharField(max_length=80, required=False)
    vat_number = forms.CharField(max_length=22, required=False)
    tin_number = forms.CharField(max_length=16, required=False)
    address = forms.CharField(required=False)
    city = forms.CharField(max_length=40, required=False)
    state = forms.CharField(max_length=2, required=False)
    zip = forms.CharField(max_length=8, required=False)
    country = forms.CharField(max_length=2, required=False)

class Speaker(forms.Form):
    bio = forms.CharField(widget=forms.Textarea())

class Talk(forms.Form):
    title = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'size': 40}))
    duration = forms.TypedChoiceField(choices=cmodels.TALK_DURATION, coerce=int, initial='30') #, emtpy_value=None)
    language = forms.TypedChoiceField(choices=cmodels.TALK_LANGUAGES, initial='en') #, emtpy_value=None)
    slides = forms.FileField(required=False)
    abstract = forms.CharField(widget=forms.Textarea())
