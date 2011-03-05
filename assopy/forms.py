# -*- coding: UTF-8 -*-
from django import forms
from django.contrib import auth
from django.db import transaction
from django.utils.translation import ugettext as _

from assopy import models
from assopy import settings
from assopy.clients import genro
from conference import models as cmodels

import logging

log = logging.getLogger('assopy.forms')

# autostrip - http://djangosnippets.org/snippets/956/
# il motivo per questo abominio?
# http://code.djangoproject.com/ticket/6362
def autostrip(cls):
    fields = [(key, value) for key, value in cls.base_fields.iteritems() if isinstance(value, forms.CharField)]
    for field_name, field_object in fields:
        def get_clean_func(original_clean):
            return lambda value: original_clean(value and value.strip())
        clean_func = get_clean_func(getattr(field_object, 'clean'))
        setattr(field_object, 'clean', clean_func)
    return cls

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

class Profile(forms.ModelForm):
    first_name = forms.CharField(
        label=_('First Name'),
        help_text=_('Please do not enter a company name here.<br />You will be able to specify billing details during the checkout.'),
        max_length=32,)
    last_name = forms.CharField(
        label=_('Last Name'),
        max_length=32,)
    class Meta:
        model = models.User
        fields = ('first_name', 'last_name', 'phone', 'www', 'twitter', 'photo')

    def __init__(self, *args, **kwargs):
        o = kwargs.get('instance')
        if o:
            initial = kwargs.get('initial', {})
            if 'first_name' not in initial:
                initial['first_name'] = o.user.first_name
            if 'last_name' not in initial:
                initial['last_name'] = o.user.last_name
            kwargs['initial'] = initial
        super(Profile, self).__init__(*args, **kwargs)

    def clean_twitter(self):
        data = self.cleaned_data.get('twitter', '')
        return data.lstrip('@')

    @transaction.commit_on_success
    def save(self, commit=True):
        data = self.cleaned_data
        self.instance.user.first_name = data['first_name']
        self.instance.user.last_name = data['last_name']
        u = super(Profile, self).save(commit=commit)
        if commit:
            self.instance.user.save()
        return u

Profile = autostrip(Profile)

class BillingData(forms.ModelForm):
    class Meta:
        model = models.User
        fields = (
            'card_name', 'account_type', 'country',
            'address', 'city', 'zip_code', 'state',
            'vat_number', 'tin_number',
        )

    def _required(self, name):
        data = self.cleaned_data.get(name, '').strip()
        if not data:
            raise forms.ValidationError('this field is required')
        return data

    clean_address = lambda self: self._required('address')
    clean_city = lambda self: self._required('city')
    clean_zip_code = lambda self: self._required('zip_code')

    def clean_card_name(self):
        data = self.cleaned_data.get('card_name', '')
        if not data:
            return self.instance.name()
        else:
            return data

BillingData = autostrip(BillingData)

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
        return email

    def clean(self):
        if not self.is_valid():
            return super(NewAccountForm, self).clean()
        data = self.cleaned_data
        if data['password1'] != data['password2']:
            raise forms.ValidationError('password mismatch')
        return data

NewAccountForm = autostrip(NewAccountForm)

class FormTickets(forms.Form):
    payment = forms.ChoiceField(choices=(('paypal', 'PayPal'),('bank', 'Bank')))
    order_type = forms.ChoiceField(choices=(('non-deductible', 'Personal Purchase'), ('deductible', 'Company Purchase')), initial='non-deductible')

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
            if k in ('payment', 'order_type'):
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
