from django import forms

from conference.models import Fare


class FormTickets(forms.Form):
    payment = forms.ChoiceField(choices=(('bank', 'Bank'),))
    order_type = forms.ChoiceField(
        choices=(
            ('non-deductible', 'Personal Purchase'),
            ('deductible', 'Company Purchase')),
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
        return Fare.objects.available()

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
