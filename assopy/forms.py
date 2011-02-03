# -*- coding: UTF-8 -*-
from django import forms
from django.contrib import auth

from assopy import models
from assopy import settings
from assopy.clients import genro
from conference import models as cmodels

import logging

log = logging.getLogger('assopy.forms')

class LoginForm(auth.forms.AuthenticationForm):
    email = forms.EmailField()

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        del self.fields['username']

    def clean(self):
        data = self.cleaned_data
        if data.get('email') and data.get('password'):
            user = auth.authenticate(email=data['email'], password=data['password'])
            self.user_cache = user
            if user is None:
                raise forms.ValidationError('Invalid credentials')
            elif not user.is_active:
                raise forms.ValidationError('This account is inactive.')
        return data

class PasswordResetForm(auth.forms.PasswordResetForm):
    def clean_email(self):
        """
        Validates that a user exists with the given e-mail address.
        """
        try:
            return super(PasswordResetForm, self).clean_email()
        except forms.ValidationError:
            # v. assopy.auth_backends.EmailBackend
            if not settings.SEARCH_MISSING_USERS_ON_BACKEND:
                raise
            email = self.cleaned_data["email"]
            rid = genro.users(email=email)['r0']
            if rid is not None:
                log.info('"%s" is a remote user; a local user is needed to reset the password', email)
                user = models.User.objects.create_from_backend(rid, email, password=None, verified=False)
                self.users_cache = auth.models.User.objects.filter(pk=user.user.pk)
                return email
            else:
                raise

class SetPasswordForm(auth.forms.SetPasswordForm):
    def save(self, *args, **kwargs):
        user = super(SetPasswordForm, self).save(*args, **kwargs)
        u = self.user.assopy_user
        if not u.verified:
            log.info('password reset for "%s" completed; now he\' a verified user', user.email)
            u.verified = True
            u.save()
        return user

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

class NewAccountForm(forms.Form):
    first_name = forms.CharField(max_length=32)
    last_name = forms.CharField(max_length=32)
    email = forms.EmailField()
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        data = self.cleaned_data
        if data['password1'] != data['password2']:
            raise forms.ValidationError('password mismatch')
        return data
