# -*- coding: UTF-8 -*-
from django import forms
from django.contrib import auth
from django.utils.translation import ugettext as _

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
                # active=True non è un problema, perchè non uso una password e
                # l'utente non può loggarsi e deve resettarla.
                user = models.User.objects.create_user(email, assopy_id=rid, active=True, send_mail=False)
                self.users_cache = auth.models.User.objects.filter(pk=user.user.pk)
                return email
            else:
                raise

class SetPasswordForm(auth.forms.SetPasswordForm):
    def save(self, *args, **kwargs):
        user = super(SetPasswordForm, self).save(*args, **kwargs)
        u = self.user.assopy_user
        # non voglio riabilitare un utente con is_active=False, voglio tenermi
        # questo flag come uno strumento di amministrazione per impedire
        # l'accesso al sito
#        if not u.verified:
#            log.info('password reset for "%s" completed; now he\' a verified user', user.email)
#            u.verified = True
#            u.save()
        return user

class Profile(forms.Form):
    firstname = forms.CharField(
        help_text=_('Please do not enter a company name here.<br />You will be able to specify billing details during the checkout.'),
        max_length=32,)
    lastname = forms.CharField(max_length=32)
    phone = forms.CharField(
        help_text=_('Enter a phone number where we can contact you in case of administrative issues.<br />Use the international format, eg: +39-055-123456'),
        max_length=30,
        required=False,)
    www = forms.URLField(label=_('Homepage'), verify_exists=False, required=False)
    twitter = forms.CharField(max_length=20, required=False)
    photo = forms.FileField(required=False)

    def clean_twitter(self):
        data = self.cleaned_data.get('twitter', '')
        return data.lstrip('@')

ACCOUNT_TYPE = (
    ('private', 'Private use'),
    ('company', 'Company'),
)
class BillingData(forms.Form):
    card_name = forms.CharField(max_length=80, required=False)
    account_type = forms.ChoiceField(choices=ACCOUNT_TYPE)
    vat_number = forms.CharField(max_length=22, required=False)
    tin_number = forms.CharField(max_length=16, required=False)
    address = forms.CharField(required=False)
    city = forms.CharField(max_length=40, required=False)
    state = forms.CharField(max_length=2, required=False)
    zip = forms.CharField(max_length=8, required=False)
    country = forms.ChoiceField(choices=models.Country.objects.order_by('printable_name').values_list('iso', 'printable_name'))

    def clean(self):
        data = self.cleaned_data
        try:
            c = models.Country.objects.get(iso=data['country'])
        except (KeyError, models.Country.DoesNotExist):
            raise forms.ValidationError('Invalid country')

        if data['account_type'] not in ('private', 'company'):
            raise forms.ValidationError('invalid account type')

        if data['account_type'] == 'private' and c.vat_person and not data.get('tin_number'):
            raise forms.ValidationError('tin number missing')
        elif data['account_type'] == 'company' and c.vat_company and not data.get('vat_company'):
            raise forms.ValidationError('vat number missing')

        return data

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
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data['email']
        if auth.models.User.objects.filter(email__iexact=email).count() > 0:
            raise forms.ValidationError('email aready in use')
        return data

    def clean(self):
        data = self.cleaned_data
        if data['password1'] != data['password2']:
            raise forms.ValidationError('password mismatch')
        return data

class FormTickets(forms.Form):
    payment = forms.ChoiceField(choices=(('paypal', 'PayPal'),('bank', 'Bank')))

    def __init__(self, *args, **kwargs):
        super(FormTickets, self).__init__(*args, **kwargs)
        for t in self.available_fares():
            self.fields[t.code] = forms.IntegerField(
                label=t.name,
                min_value=0,
                required=False,
            )

    def available_fares(self):
        return cmodels.Fare.objects.available()

    def clean(self):
        fares = dict( (x.code, x) for x in self.available_fares() )
        data = self.cleaned_data
        o = []
        total = 0
        for k, q in data.items():
            if k in ('payment',):
                continue
            if not q:
                continue
            if k not in fares:
                self._errors[k] = self.error_class(['Invalid fare'])
                del data[k]
                continue
            total += q
            f = fares[k]
            if not f.valid():
                self._errors[k] = self.error_class(['Invalid fare'])
                del data[k]
                continue
            o.append((f, q))
        if total == 0:
            raise forms.ValidationError('no tickets')

        data['tickets'] = o
        return data
