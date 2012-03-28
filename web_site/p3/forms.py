# -*- coding: UTF-8 -*-
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.translation import ugettext as _

import assopy.models as amodels
import assopy.forms as aforms
import conference.forms as cforms 
import conference.models as cmodels

from p3 import dataaccess
from p3 import models

import datetime

class P3SubmissionForm(cforms.SubmissionForm):
    duration = forms.TypedChoiceField(
        label=_('Duration'),
        help_text=_('This is the <b>suggested net duration</b> of the talk, excluding Q&A'),
        choices=((45, '30 minutes'), (60, '45 minutes'), (90, '70 minutes'), (240, '4 hours')),
        coerce=int,
        initial=60,
        required=False,
    )
    first_time = forms.BooleanField(
        label=_('I\'m a first-time speaker'),
        help_text=_('We are planning a special program to help first time speaker, check this if you\'d like to join'),
        required=False,
    )
    type = forms.TypedChoiceField(
        label=_('Talk Type'),
        help_text='Choose between a standard talk, a 4-hours in-depth training or a poster session',
        choices=(('s', 'Standard talk'), ('t', 'Training'), ('p', 'Poster session'),),
        initial='s',
        required=True,
        widget=forms.RadioSelect(renderer=cforms.PseudoRadioRenderer),
    )
    personal_agreement = forms.BooleanField(
        label=_('I agree to let you publish my data (excluding birth date and phone number).'),
        help_text=_('This speaker profile will be publicly accesible if one of your talks is accepted. Your mobile phone and date of birth will <strong>never</strong> be published'),
    )
    slides_agreement = forms.BooleanField(
        label=_('I agree to release all the talk material after the event.'),
        help_text=_('If the talk is accepted, speakers a required to timely release all the talk material (including slides) for publishing on this web site.'),
    )
    video_agreement = forms.BooleanField(
        label=_('I agree to let the organization record my talk and publish the video.'),
    )
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=cforms.MarkEditWidget,)
    abstract = forms.CharField(
        max_length=5000,
        label=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'),
        widget=cforms.MarkEditWidget,)

    language = forms.TypedChoiceField(
        help_text=_('Select Italian only if you are not comfortable in speaking English.'),
        choices=cmodels.TALK_LANGUAGES,
        initial='en', required=False)

    def __init__(self, user, *args, **kwargs):
        data = {
            'mobile': user.assopy_user.phone,
            'birthday': user.assopy_user.birthday,
            'activity_homepage': user.assopy_user.www,
        }
        data.update(kwargs.get('initial', {}))
        kwargs['initial'] = data
        super(P3SubmissionForm, self).__init__(user, *args, **kwargs)

    def clean(self):
        data = super(P3SubmissionForm, self).clean()
        if data['type'] == 't':
            data['duration'] = 240

        if not data.get('duration'):
            data['duration'] = 45

        if not data.get('language') or data['type'] != 's':
            data['language'] = 'en'

        return data

    @transaction.commit_on_success
    def save(self, *args, **kwargs):
        talk = super(P3SubmissionForm, self).save(*args, **kwargs)

        speaker = self.user.speaker
        try:
            p3s = speaker.p3_speaker
        except models.SpeakerConference.DoesNotExist:
            p3s = models.SpeakerConference(speaker=speaker)
            
        data = self.cleaned_data

        p3s.first_time = data['first_time']
        p3s.save()

        return talk

class P3SubmissionAdditionalForm(cforms.TalkForm):
    duration = forms.TypedChoiceField(
        label=_('Duration'),
        help_text=_('This is the <b>suggested net duration</b> of the talk, excluding Q&A'),
        choices=((45, '30 minutes'), (60, '45 minutes'), (90, '70 minutes'), (240, '4 hours')),
        coerce=int,
        initial=60,
        required=False,
    )
    slides_agreement = forms.BooleanField(
        label=_('I agree to release all the talk material after the event.'),
        help_text=_('If the talk is accepted, speakers a required to timely release all the talk material (including slides) for publishing on this web site.'),
    )
    video_agreement = forms.BooleanField(
        label=_('I agree to let the organization record my talk and publish the video.'),
    )
    type = forms.TypedChoiceField(
        label=_('Talk Type'),
        help_text='Choose between a standard talk, a 4-hours in-depth training or a poster session',
        choices=(('s', 'Standard talk'), ('t', 'Training'), ('p', 'Poster session'),),
        initial='s',
        required=True,
        widget=forms.RadioSelect(renderer=cforms.PseudoRadioRenderer),
    )
    abstract = forms.CharField(
        max_length=5000,
        label=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'),
        widget=cforms.MarkEditWidget,)

    language = forms.TypedChoiceField(
        help_text=_('Select Italian only if you are not comfortable in speaking English.'),
        choices=cmodels.TALK_LANGUAGES,
        initial='en', required=False)

    def clean(self):
        data = super(P3SubmissionAdditionalForm, self).clean()
        if data['type'] == 't':
            data['duration'] = 240

        if not data.get('duration'):
            data['duration'] = 45

        if not data.get('language') or data['type'] != 's':
            data['language'] = 'en'
        return data

class P3TalkForm(cforms.TalkForm):
    duration = forms.TypedChoiceField(
        label=_('Duration'),
        help_text=_('This is the <b>suggested net duration</b> of the talk, excluding Q&A'),
        choices=((45, '30 minutes'), (60, '45 minutes'), (90, '70 minutes'), (240, '4 hours')),
        coerce=int,
        initial=60,
        required=False,
    )
    type = forms.TypedChoiceField(
        label=_('Talk Type'),
        help_text='Choose between a standard talk, a 4-hours in-depth training or a poster session',
        choices=(('s', 'Standard talk'), ('t', 'Training'), ('p', 'Poster session'),),
        initial='s',
        required=True,
        widget=forms.RadioSelect,
    )
    abstract = forms.CharField(
        max_length=5000,
        label=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'),
        widget=cforms.MarkEditWidget,)
    teaser_video = forms.URLField(
        label=_('Teaser video'),
        help_text=_('Insert the url for your teaser video'),
        required=False,
        widget=forms.TextInput(attrs={'size': 40}),
    )

    def clean(self):
        data = super(P3TalkForm, self).clean()
        # se instance è None la form viene usata per presentare un nuovo paper
        if not self.instance:
            if data['type'] == 't':
                data['duration'] = 240

            if not data.get('duration'):
                data['duration'] = 45

            if not data.get('language') or data['type'] != 's':
                data['language'] = 'en'
        return data

class P3SpeakerForm(cforms.SpeakerForm):
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=cforms.MarkEditWidget,)

class FormTicket(forms.ModelForm):
    ticket_name = forms.CharField(max_length=60, required=False, help_text='name of the attendee')
    days = forms.MultipleChoiceField(label=_('Probable days of attendance:'), choices=tuple(), widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = models.TicketConference
        exclude = ('ticket',)
        widgets = {
            'assigned_to': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        single_day = kwargs.pop('single_day', False)
        if kwargs.get('instance'):
            data = {
                'days': kwargs['instance'].days.split(','),
            }
            data.update(kwargs.get('initial', {}))
            kwargs['initial'] = data
        if single_day:
            if 'initial' in kwargs and kwargs['initial'].get('days', []):
                kwargs['initial']['days'] = kwargs['initial']['days'][0]
        super(FormTicket, self).__init__(*args, **kwargs)
        self.single_day = single_day
        if single_day:
            self.fields['days'] = forms.ChoiceField(
                label=_('Days'), choices=tuple(), widget=forms.RadioSelect, required=False)

        days = []
        conf = cmodels.Conference.objects.current()
        d = conf.conference_start
        while d <= conf.conference_end:
            days.append((d.strftime('%Y-%m-%d'), d.strftime('%a, %d %b')))
            d = d + datetime.timedelta(days=1)
        self.fields['days'].choices = days

    def clean_days(self):
        raw = self.cleaned_data.get('days')
        if self.single_day:
            raw = [ raw ]
        try:
            data = map(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'), filter(None, raw))
        except Exception, e:
            raise forms.ValidationError('formato data non valido')
        conf = cmodels.Conference.objects.current()
        days = []
        for x in data:
            if conf.conference_start <= x.date() <= conf.conference_end:
                days.append(x.strftime('%Y-%m-%d'))
            else:
                raise forms.ValidationError('data non valida')
        if self.single_day:
            return days[0] if days else ''
        else:
            return ','.join(days)

    def clean(self):
        data = self.cleaned_data
        if not data.get('ticket_name') and not data.get('assigned_to'):
            forms.ValidationError('invalid name')
        return data

class FormTicketPartner(forms.ModelForm):
    name = forms.CharField(max_length=60, required=False, help_text='Real name of the person that will attend this specific event.')
    class Meta:
        model = cmodels.Ticket
        fields = ('name',)

class FormTicketSIM(forms.ModelForm):
    ticket_name = forms.CharField(max_length=60, help_text='The SIM owner')
    class Meta:
        model = models.TicketSIM
        exclude = ('ticket',)
        fields = ('ticket_name', 'sim_type', 'plan_type', 'document',)

class FormTicketRoom(forms.ModelForm):
    ticket_name = forms.CharField(max_length=60, help_text='The person who will stay at the hotel')
    class Meta:
        model = models.TicketRoom
        exclude = ('ticket',)
        fields = ('ticket_name', 'document', 'unused')

class FormSprint(forms.ModelForm):
    class Meta:
        model = models.Sprint
        exclude = ('user', 'conference',)

class P3ProfileForm(cforms.ProfileForm):
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=cforms.MarkEditWidget,
        required=False,)
    tagline = forms.CharField(
        label=_('Tagline'),
        help_text=_('Describe yourself in one line'),
        required=False,
    )
    interests = cforms.TagField(label="Technical interests", widget=cforms.TagWidget, required=False)
    twitter = forms.CharField(max_length=80, required=False)
    visibility = forms.ChoiceField(choices=cmodels.ATTENDEEPROFILE_VISIBILITY, widget=forms.RadioSelect, required=False)

    image_gravatar= forms.BooleanField(required=False, widget=forms.HiddenInput)
    image_url = forms.URLField(required=False)
    image = forms.FileField(required=False, widget=forms.FileInput)

    def __init__(self, *args, **kw):
        i = kw.get('instance')
        if i:
            try:
                p3p = i.p3_profile
            except models.P3Profile.DoesNotExist:
                pass
            else:
                initial = kw.get('initial', {})
                initial.update({
                    'tagline': p3p.tagline,
                    'interests': p3p.interests.all(),
                    'twitter': p3p.twitter,
                    'image_gravatar': p3p.image_gravatar,
                    'image_url': p3p.image_url,
                })
                kw['initial'] = initial
        super(P3ProfileForm, self).__init__(*args, **kw)

    def clean(self):
        data = self.cleaned_data
        data['visibility'] = data.get('visibility', 'x')
        return data

    def clean_twitter(self):
        data = self.cleaned_data.get('twitter', '')
        if data.startswith('@'):
            data = data[1:]
        return data
    
    def save(self, commit=True):
        assert commit, "Aggiornare P3ProfileForm per funzionare con commit=False"
        profile = super(P3ProfileForm, self).save(commit=commit)
        try:
            p3p = profile.p3_profile
        except models.P3Profile.DoesNotExist:
            p3p = models.P3Profile(profile=profile)
            p3p.save()
        return profile


class P3ProfilePublicDataForm(P3ProfileForm):
    class Meta:
        model = cmodels.AttendeeProfile
        fields = ('tagline', 'personal_homepage', 'interests', 'twitter', 'company', 'company_homepage', 'job_title', 'location',)

    def clean_bio(self):
        return getattr(self.instance.getBio(), 'body', '')

    def save(self, commit=True):
        try:
            oldl = cmodels.AttendeeProfile.objects\
                .values('location')\
                .get(user=self.instance.user_id)['location']
        except (AttributeError, cmodels.AttendeeProfile.DoesNotExist), e:
            oldl = None
        profile = super(P3ProfilePublicDataForm, self).save(commit)
        p3p = profile.p3_profile
        data = self.cleaned_data
        p3p.tagline = data.get('tagline', '')
        p3p.twitter = data.get('twitter', '')

        loc = data.get('location')
        if loc:
            if loc != oldl:
                from assopy.utils import geocode_country
                p3p.country = geocode_country(loc)
        else:
            p3p.country = ''

        p3p.save()
        p3p.interests.set(*data.get('interests', ''))
        return profile

class P3ProfileBioForm(P3ProfileForm):
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=cforms.MarkEditWidget,
        required=False,)
    class Meta:
        model = cmodels.AttendeeProfile
        fields = ()
    def save(self, commit=True):
        profile = super(P3ProfileBioForm, self).save(commit)
        data = self.cleaned_data
        profile.setBio(data.get('bio', ''))
        return profile

class P3ProfileVisibilityForm(P3ProfileForm):
    visibility = forms.ChoiceField(choices=cmodels.ATTENDEEPROFILE_VISIBILITY, widget=forms.RadioSelect)
    class Meta:
        model = cmodels.AttendeeProfile
        fields = ('visibility',)

    def clean_bio(self):
        return getattr(self.instance.getBio(), 'body', '')

class P3ProfilePictureForm(P3ProfileForm):
    opt = forms.ChoiceField(choices=(
            ('x', 'no picture'),
            ('g', 'use gravatar'),
            ('u', 'use url'),
            ('f', 'upload file'),
        ), required=False)
    image_gravatar= forms.BooleanField(required=False, widget=forms.HiddenInput)
    image_url = forms.URLField(required=False)
    image = forms.FileField(required=False, widget=forms.FileInput)

    class Meta:
        model = cmodels.AttendeeProfile
        fields = ('image',)

    def clean_bio(self):
        return getattr(self.instance.getBio(), 'body', '')

    def clean(self):
        data = self.cleaned_data
        opt = data.get('opt', 'x')
        if opt == 'x':
            data['image'] = False
            data['image_gravatar'] = False
            data['image_url'] = ''
        elif opt == 'g':
            data['image'] = False
            data['image_gravatar'] = True
            data['image_url'] = ''
        elif opt == 'u':
            data['image'] = False
            data['image_gravatar'] = False
        elif opt == 'f':
            data['image_gravatar'] = False
            data['image_url'] = ''
        return data

    def save(self, commit=True):
        profile = super(P3ProfilePictureForm, self).save(commit)
        p3p = profile.p3_profile
        data = self.cleaned_data
        p3p.image_gravatar = data.get('image_gravatar', False)
        p3p.image_url = data.get('image_url', '')
        p3p.save()
        return profile

class P3ProfilePersonalDataForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    phone = forms.CharField(
        help_text=_('If you opt-in the privacy settings, we can send you important communications via SMS.<br />Use the international format, eg: +39-055-123456.<br/>This number will <strong>never</strong> be published.'),
        max_length=30,
        required=False,
    )
    birthday = forms.DateField(
        label=_('Date of birth'),
        help_text=_('We require date of birth for speakers to accomodate for Italian laws regarding minors.<br />Format: YYYY-MM-DD<br />This date will <strong>never</strong> be published.'),
        input_formats=('%Y-%m-%d',),
        widget=forms.DateInput(attrs={'size': 10, 'maxlength': 10}),
        required=False,
    )

    class Meta:
        model = cmodels.AttendeeProfile
        fields = ('phone', 'birthday')

    def clean_phone(self):
        value = self.cleaned_data.get('phone', '')
        try:
            self.instance.user.speaker
        except (AttributeError, User.DoesNotExist, cmodels.Speaker.DoesNotExist):
            pass
        else:
            if not value:
                raise forms.ValidationError('This field is required for a speaker')
        return value

    def clean_birthday(self):
        value = self.cleaned_data.get('birthday', '')
        try:
            self.instance.user.speaker
        except (AttributeError, User.DoesNotExist, cmodels.Speaker.DoesNotExist):
            pass
        else:
            if not value:
                raise forms.ValidationError('This field is required for a speaker')
        return value

class P3ProfileEmailContactForm(forms.Form):
    email = forms.EmailField(label="Enter new email")

class P3ProfileSpamControlForm(forms.ModelForm):
    spam_recruiting = forms.BooleanField(label='I want to receive a few selected job offers through EuroPython.', required=False)
    spam_user_message = forms.BooleanField(label='I want to receive private messages from other partecipants.', required=False)
    spam_sms = forms.BooleanField(label='I want to receive SMS during the conference for main communications.', required=False)
    class Meta:
        model = models.P3Profile
        fields = ('spam_recruiting', 'spam_user_message', 'spam_sms')

class HotelReservationsFieldWidget(forms.Widget):
    def value_from_datadict(self, data, files, name):
        if name in data:
            # data è l'initial_data, contiene i dati già in forma normalizzata
            return data[name]
        # data è un QueryDict, o cmq proviene da una request
        fares = data.getlist(name + '_fare')
        qtys = data.getlist(name + '_qty')
        periods = data.getlist(name + '_period')

        # qualcuno si è messo a giocare con i dati in ingresso, interrompo
        # tutto inutile passare per la validazione
        if len(fares) != len(qtys) or len(periods) != len(fares) * 2:
            raise ValueError('')

        from itertools import izip_longest
        def grouper(n, iterable, fillvalue=None):
            "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
            args = [iter(iterable)] * n
            return izip_longest(fillvalue=fillvalue, *args)

        start = settings.P3_HOTEL_RESERVATION['period'][0]
        values = []
        for row in zip(fares, qtys, grouper(2, periods)):
            values.append({
                'fare': row[0],
                'qty': row[1],
                'period': map(lambda x: start+datetime.timedelta(days=int(x)), row[2]),
            })

        return values

    def render(self, name, value, attrs=None):
        try:
            start = settings.P3_HOTEL_RESERVATION['period'][0]
        except:
            raise TypeError('P3_HOTEL_RESERVATION not set')

        from django.template.loader import render_to_string
        from conference import dataaccess as cdataaccess

        tpl = 'p3/fragments/form_field_hotel_reservation_widget.html'
        fares = {
            'HR': [],
            'HB': [],
        }
        for f in cdataaccess.fares(settings.CONFERENCE_CONFERENCE):
            if not f['valid']:
                continue
            if f['code'][:2] == 'HR':
                fares['HR'].append(f)
            elif f['code'][:2] == 'HB':
                fares['HB'].append(f)

        if not fares['HR'] or not fares['HB']:
            return ''

        if not value:
            value = [
                {'fare': fares['HB'][0]['code'], 'qty': 0, 'period': settings.P3_HOTEL_RESERVATION['default']},
                {'fare': fares['HR'][0]['code'], 'qty': 0, 'period': settings.P3_HOTEL_RESERVATION['default']},
            ]

        types = getattr(self, 'types', ['HR', 'HB'])
        rows = []
        for entry in value:
            k = entry['fare'][:2]
            if k not in ('HR', 'HB'):
                raise TypeError('unsupported fare')
            if k not in types:
                continue
            ctx = {
                'label': '',
                'type': '',
                'qty': entry['qty'],
                'period': map(lambda x: (x-start).days, entry['period']),
                'fare': entry['fare'],
                'fares': [],
            }
            if k == 'HB':
                ctx['label'] = _('Room sharing')
                ctx['type'] = 'bed'
                ctx['fares'] = fares['HB']
            else:
                ctx['label'] = _('Full room')
                ctx['type'] = 'room'
                ctx['fares'] = fares['HR']

            rows.append(ctx)

        # XXX schifezza!
        # per come ho implementato il rendering del widget ho bisogno di sapere
        # qui e adesso se ci sono errori per mostrarli nel posto giusto.
        # Purtroppo gli errori sono una proprietà del BoundField non del field
        # ne tantomeno del widget. Questo codice è un accrocchio funziona
        # perché nel templatetag aggancio al widget gli errori della form. Il
        # modo pulito sarebbe implementare il rendering dei subwidget come
        # avviene per il RadioInput, passare dal filtro |field e inserire li
        # gli errori.
        errors = [None] * len(rows)
        if hasattr(self, '_errors'):
            print self._errors
            for e in self._errors:
                try:
                    ix, msg = e.split(':', 1)
                except ValueError:
                    continue
                try:
                    errors[int(ix)] = msg
                except:
                    continue
        for e in zip(rows, errors):
            if e[1]:
                e[0]['error'] = e[1]

        ctx = {
            'start': start,
            'days': (settings.P3_HOTEL_RESERVATION['period'][1]-start).days,
            'rows': rows,
            'name': name,
        }
        return render_to_string(tpl, ctx)

class HotelReservationsField(forms.Field):
    widget = HotelReservationsFieldWidget

    def __init__(self, types=('HR', 'HB'), *args, **kwargs):
        super(HotelReservationsField, self).__init__(*args, **kwargs)
        self.widget.types = types

    def clean(self, value):
        for ix, entry in reversed(list(enumerate(value))):
            try:
                entry['qty'] = int(entry['qty'].strip() or '0')
            except (ValueError, TypeError):
                raise forms.ValidationError('invalid quantity')
            if not entry['qty']:
                del value[ix]
        return value

class P3FormTickets(aforms.FormTickets):
    coupon = forms.CharField(
        label='Insert your discount code and save money!',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'size': 10}),
    )
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(P3FormTickets, self).__init__(*args, **kwargs)
        # cancello il campo pagamento perché voglio posticipare questa scelta
        del self.fields['payment']

        # i field relativi alle prenotazioni alberghiere si comportano in
        # maniera speciale; innanzitutto possono essere "multipli" nel senso
        # che per la stesso tipo di fare (ad esempio HB3 - posto letto in
        # tripla) posso avere entry in periodi diversi (ogni entry può già
        # specificare il numero di posti letto disponibili).
        # Inoltre per ogni prenotazione deve essere specificato anche il "periodo".

        # Decido di gestire questi casi con del codice custom nella clean
        for k in self.fields.keys():
            if k.startswith('H'):
                del self.fields[k]
        
        self.fields['room_reservations'] = HotelReservationsField(types=('HR',), required=False)
        self.fields['bed_reservations'] = HotelReservationsField(types=('HB',), required=False)

    def clean_coupon(self):
        data = self.cleaned_data.get('coupon', '').strip()
        if not data:
            return None
        if data[0] == '_':
            raise forms.ValidationError('invalid coupon')
        try:
            coupon = amodels.Coupon.objects.get(code__iexact=data)
        except amodels.Coupon.DoesNotExist:
            raise forms.ValidationError('invalid coupon')
        if not coupon.valid(self.user):
            raise forms.ValidationError('invalid coupon')
        return coupon

    def _check_hotel_reservation(self, field_name):
        data = self.cleaned_data.get(field_name, [])
        if not data:
            return []

        checks = []
        for ix, row in enumerate(data):
            f = cmodels.Fare.objects.get(code=row['fare'])
            price = f.calculated_price(**row)
            if not price:
                raise forms.ValidationError('%s:invalid period' % ix)

            checks.append((
                't' + f.code[2],
                row['qty'] * (1 if f.code[1] == 'B' else int(f.code[2])),
                row['period'],
            ))

        # voglio permettere l'acquisito solo ai partecipanti
        conference_tickets = 0
        for k, v in self.cleaned_data.items():
            if k[0] == 'T' and v:
                conference_tickets += v
        if not conference_tickets:
            from p3.dataaccess import user_tickets
            tickets = user_tickets(self.user.user, settings.CONFERENCE_CONFERENCE, only_complete=True)
            for t in tickets:
                if t.fare.code.startswith('T'):
                    conference_tickets += 1
        if not conference_tickets:
            args = []
            for ix, _ in enumerate(data):
                args.append('%s:You need a conference ticket' % ix)
            self._errors[field_name] = self.error_class(args)
            del self.cleaned_data[field_name]

        try:
            models.TicketRoom.objects.can_be_booked(checks)
        except ValueError:
            raise forms.ValidationError('0:Not available in this period (<a href="/hotel-concession/rooms-not-available" class="trigger-overlay">info</a>)')

        return data

    def clean_bed_reservations(self):
        return self._check_hotel_reservation('bed_reservations')

    def clean_room_reservations(self):
        return self._check_hotel_reservation('room_reservations')

    def clean(self):
        data = super(P3FormTickets, self).clean()

        order_type = data['order_type']
        company = order_type == 'deductible'
        for ix, row in list(enumerate(data['tickets']))[::-1]:
            fare = row[0]
            if fare.ticket_type != 'company':
                continue
            if (company ^ (fare.code[-1] == 'C')):
                del data['tickets'][ix]
                del data[fare.code]

        from conference.models import Fare
        for fname in ('bed_reservations', 'room_reservations'):
            for r in data.get(fname, []):
                data['tickets'].append((Fare.objects.get(code=r['fare']), r))

        if not data['tickets']:
            raise forms.ValidationError('No tickets')

        return data

class P3EventBookingForm(cforms.EventBookingForm):
    def clean_value(self):
        data = super(P3EventBookingForm, self).clean_value()
        if data:
            tickets = dataaccess.all_user_tickets(self.user, conference=settings.CONFERENCE_CONFERENCE)
            for tid, ttype, fcode, complete in tickets:
                if complete and ttype == 'conference' and fcode[2] == 'S':
                    break
            else:
                raise forms.ValidationError('ticket error')
        return data
