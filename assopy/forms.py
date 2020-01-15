from django import forms
from django.utils.translation import ugettext as _

from assopy import models
from conference import models as cmodels

import logging

log = logging.getLogger('assopy.forms')


# autostrip - http://djangosnippets.org/snippets/956/
# il motivo per questo abominio?
# http://code.djangoproject.com/ticket/6362
def autostrip(cls):
    fields = [(key, value) for key, value in cls.base_fields.items() if isinstance(value, forms.CharField)]
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



class Profile(forms.ModelForm):
    first_name = forms.CharField(
        label=_('First Name'),
        help_text=_('Please do not enter a company name here.<br />You will be able to specify billing details during the checkout.'),
        max_length=32,)
    last_name = forms.CharField(
        label=_('Last Name'),
        max_length=32,)
    class Meta:
        model = models.AssopyUser
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


class FormTickets(forms.Form):
    payment = forms.ChoiceField(choices=(('bank', 'Bank'),))
    order_type = forms.ChoiceField(
        choices=(
            ('non-deductible', _('Personal Purchase')),
            ('deductible', _('Company Purchase'))),
        initial='non-deductible')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
