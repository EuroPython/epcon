# -*- coding: utf-8 -*-

from django import forms
from django.contrib import auth
from django.conf import settings as dsettings
from django.utils.translation import ugettext as _

from assopy import models
from assopy import settings
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


PRIVACY_POLICY_CHECKBOX = """
I consent to the use of my data subject to the <a href='/privacy/'>EuroPython
data privacy policy</a>
""".strip()

PRIVACY_POLICY_ERROR = """
You need to consent to use of your data before we can continue
""".strip()


class LoginForm(auth.forms.AuthenticationForm):
    email = forms.EmailField()
    i_accept_privacy_policy = forms.BooleanField(
        label=PRIVACY_POLICY_CHECKBOX
    )

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        del self.fields['username']

    def clean(self):
        data = self.cleaned_data
        if not data.get('i_accept_privacy_policy'):
            raise forms.ValidationError(PRIVACY_POLICY_ERROR)

        if data.get('email') and data.get('password'):
            user = auth.authenticate(email=data['email'],
                                     password=data['password'])
            self.user_cache = user
            if user is None:
                raise forms.ValidationError('Invalid credentials')
            elif not user.is_active:
                raise forms.ValidationError('This account is inactive.')
        return data


class SetPasswordForm(auth.forms.SetPasswordForm):
    def save(self, *args, **kwargs):
        user = super(SetPasswordForm, self).save(*args, **kwargs)
#        u = self.user.assopy_user
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
        fields = ('first_name', 'last_name')

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
        exclude = ('user', 'token', 'assopy_id')

    def _required(self, name):
        data = self.cleaned_data.get(name, '')
        try:
            data = data.strip()
        except:
            pass
        if not data:
            raise forms.ValidationError('this field is required')
        return data

    clean_country = lambda self: self._required('country')
    clean_address = lambda self: self._required('address')

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
    password1 = forms.CharField(label="Password",
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password",
                                widget=forms.PasswordInput)

    # Additional captcha field with simple python questions
    # https://github.com/EuroPython/epcon/issues/703
    captcha_question = forms.CharField(widget=forms.HiddenInput)
    captcha_answer = forms.CharField()

    # Keep this in sync with LoginForm.i_accept_privacy_policy
    i_accept_privacy_policy = forms.BooleanField(
        label=PRIVACY_POLICY_CHECKBOX
    )

    def __init__(self, *args, **kwargs):
        super(NewAccountForm, self).__init__(*args, **kwargs)
        random_question = self.get_random_captcha_question()
        if random_question:
            self.fields['captcha_question'].initial = random_question.question
            self.fields['captcha_answer'].label     = random_question.question
        else:
            del self.fields['captcha_question']
            del self.fields['captcha_answer']

    def get_random_captcha_question(self):
        try:
            return cmodels.CaptchaQuestion.objects.get_random_question()
        except cmodels.CaptchaQuestion.NoQuestionsAvailable:
            return None

    def clean_captcha_answer(self):
        question = self.cleaned_data['captcha_question']
        cq = cmodels.CaptchaQuestion.objects.get(question=question)
        if cq.answer.strip() != self.cleaned_data['captcha_answer'].strip():
            raise forms.ValidationError("Sorry, that's a wrong answer")
        return self.cleaned_data['captcha_question']

    def clean_email(self):
        email = self.cleaned_data['email']
        if auth.models.User.objects.filter(email__iexact=email).count() > 0:
            raise forms.ValidationError('Email already in use')

        return email.lower()

    def clean(self):
        if not self.cleaned_data.get('i_accept_privacy_policy'):
            raise forms.ValidationError(PRIVACY_POLICY_ERROR)

        if not self.is_valid():
            return super(NewAccountForm, self).clean()

        data = self.cleaned_data
        if data['password1'] != data['password2']:
            raise forms.ValidationError('password mismatch')
        return data


NewAccountForm = autostrip(NewAccountForm)


class FormTickets(forms.Form):
    payment = forms.ChoiceField(choices=(('bank', 'Bank')))
    order_type = forms.ChoiceField(
        choices=(
            ('non-deductible', _('Personal Purchase')),
            ('deductible', _('Company Purchase'))),
        initial='non-deductible')

    def __init__(self, *args, **kwargs):
        super(FormTickets, self).__init__(*args, **kwargs)
        for t in self.available_fares():
            field = forms.IntegerField(
                label=t.name,
                min_value=0,
                required=False,
            )
            field.fare = t
            self.fields[t.code] = field

    def available_fares(self):
        return cmodels.Fare.objects.available()

    def clean(self):
        fares = dict( (x.code, x) for x in self.available_fares() )
        data = self.cleaned_data
        o = []
        total = 0
        for k, q in data.items():
            if k not in fares:
                continue
            if not q:
                continue
            total += q
            f = fares[k]
            if not f.valid():
                self._errors[k] = self.error_class(['Invalid fare'])
                del data[k]
                continue
            o.append((f, {'qty': q}))

        data['tickets'] = o
        return data

class RefundItemForm(forms.Form):
    reason = forms.CharField(
        label=_("Reason"),
        max_length=200,
        help_text=_("""Please enter the reason of your refund request"""),
        widget=forms.Textarea)
    bank = forms.CharField(
        label=_("Bank routing information"),
        help_text=_("""Please specify IBAN, BIC and bank address (if in Europe) or any needed information for a worldwide transfer"""),
        required=False,
        widget=forms.Textarea)

    def __init__(self, item, *args, **kw):
        super(RefundItemForm, self).__init__(*args, **kw)
        self.item = item

    def clean(self):
        data = self.cleaned_data
        if self.item.refund_type() == 'payment':
            if not data.get('bank'):
                raise forms.ValidationError('Please specify  the bank details')
        return data

