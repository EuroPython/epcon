# -*- coding: utf-8 -*-
import datetime

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

### Globals

## These should really be changes in the conference package:

# TBD: These forms need some cleanup. Probably best to merge the
# conference repo into epcon and then remove all this subclassing.

class P3TalkFormMixin(object):
    def clean(self):
        data = super(P3TalkFormMixin, self).clean()

        # You can select the right duration now, so this is no longer
        # needed
        #if data['type'] in ('t', 'h'):
        #    data['duration'] = 240
        # Set default language
        if not data.get('language'):
            data['language'] = 'en'
        return data


# This form is used for new talk submissions and only when the speaker
# has not yet submitted another talk; see P3SubmissionAdditionalForm
# for talk editing and additional talks.

# Hot topic CFP only allows a subset of available talk types:
#TALK_TYPE_FORM = list((
#    ('t_30', 'Talk (30 mins)'),
#    ('t_45', 'Talk (45 mins)'),
##    ('t_60', 'Talk (60 mins)'),
##    ('i_60', 'Interactive (60 mins)'),
##    ('r_180', 'Training (180 mins)'),
#    ('p_180', 'Poster session (180 mins)'),
##    ('n_60', 'Panel (60 mins)'),
##    ('n_90', 'Panel (90 mins)'),
#    ('h_180', 'Help desk (180 mins)'),
#))

# Normal CFP:
TALK_TYPE_FORM = list(cmodels.TALK_TYPE)

# Add a non-valid default choice for the talk type to force the user
# to select one
TALK_TYPE_FORM.insert(0, ("", "----------------"))

class P3SubmissionForm(P3TalkFormMixin, cforms.SubmissionForm):
    #first_time = forms.BooleanField(
    #    label=_('I\'m a first-time speaker'),
    #    help_text=_('This setting will be visible for the Program WG to use in their talk selection. The WG may contact you to ask you to participate in a first time speaker training session.'),
    #    required=False,
    #)
    type = forms.TypedChoiceField(
        label=_('Submission type'),
        help_text='Choose between a standard talk, an in-depth training, a poster session or an help desk session',
        choices=TALK_TYPE_FORM,
        required=True,
    )

    # Note: These three fields are *not* saved in the talk record,
    # they are just used to show the checkboxes when first submitting
    # a talk and required, so that no talk can be submitted without
    # checking them.
    personal_agreement = forms.BooleanField(
        label=_('I agree to let you publish my profile data (excluding birth date and phone number).'),
        help_text=_('The speaker profile will be publicly accessible if one of your talks is accepted. Your mobile phone and date of birth will <i>never</i> be published'),
    )
    slides_agreement = forms.BooleanField(
        label=_('I agree to upload my presentation material after the event to this web site.'),
        help_text=_('If the talk is accepted, speakers are encouraged to upload their talk slides to make them available to users of this web site.'),
    )
    video_agreement = forms.BooleanField(
        label=_('I agree to have my presentation recorded and have read, understood and agree to the <a href="/speaker-release-agreement/">EuroPython Speaker Release Agreement</a>'),
        help_text=_('We will be recording the conference talks and publish them on the EuroPython YouTube channel and archive.org.'),
    )

    domain = forms.ChoiceField(
        label=_('Domain / Track'),
        help_text=_('Select the domain / track suggestion for the talk. This will help us with the conference scheduling.'),
        choices=settings.CONFERENCE_TALK_DOMAIN,
        initial='',
        required=False)

    domain_level = forms.ChoiceField(
        label=_('Domain Expertise'),
        help_text=_('The domain expertise your audience should have to follow along (e.g. how much should one know about DevOps or Data Science already)'),
        choices=cmodels.TALK_LEVEL,
        initial=cmodels.TALK_LEVEL.beginner,
        required=False)

    def __init__(self, user, *args, **kwargs):
        data = {}
        data.update(kwargs.get('initial', {}))
        kwargs['initial'] = data
        super(P3SubmissionForm, self).__init__(user, *args, **kwargs)

    #@transaction.atomic
    def save(self, *args, **kwargs):
        talk = super(P3SubmissionForm, self).save(*args, **kwargs)

        speaker = self.user.speaker
        try:
            p3s = speaker.p3_speaker
        except models.SpeakerConference.DoesNotExist:
            p3s = models.SpeakerConference(speaker=speaker)

        data = self.cleaned_data

        p3s.first_time = data.get('first_time', False)
        p3s.save()

        # Set additional fields added in this form (compared to
        # cforms.SubmissionForm)
        models.P3Talk.objects.get_or_create(talk=talk)

        return talk



# This form is used in case the speaker has already proposed a talk
# and for editing talks

class P3SubmissionAdditionalForm(P3TalkFormMixin, cforms.TalkForm):
    slides_agreement = P3SubmissionForm.base_fields['slides_agreement']
    video_agreement = P3SubmissionForm.base_fields['video_agreement']
    type = P3SubmissionForm.base_fields['type']
    domain = forms.ChoiceField(
        label=_('Domain / Track'),
        help_text=_('Select the domain of the talk, this will help us with the conference scheduling.'),
        choices=settings.CONFERENCE_TALK_DOMAIN,
        initial='',
        required=False)

    domain_level = forms.ChoiceField(
        label=_('Domain Expertise'),
        help_text=_('The domain expertise your audience should have to follow along (e.g. how much should one know about DevOps or Data Science already)'),
        choices=cmodels.TALK_LEVEL,
        initial='',
        required=False)

    class Meta(cforms.TalkForm.Meta):
        exclude = ('duration', )

    def __init__(self, *args, **kwargs):
        super(P3SubmissionAdditionalForm, self).__init__(*args, **kwargs)
        if self.instance:
            # The speaker has already agreed to these when submitting
            # the first talk, so preset them
            self.fields['slides_agreement'].initial = True
            self.fields['video_agreement'].initial = True

    def save(self, *args, **kwargs):
        # TODO/FIXME(artcz) – added this from P3SubmissionForm, because talks
        # submitted via this form later complained about P3Talk missing.
        # However I'm not sure if we even need that, but due to time
        # constraints we can't refactors this right now.
        # Set additional fields added in this form (compared to
        # cforms.SubmissionForm)
        talk = super(P3SubmissionAdditionalForm, self).save(*args, **kwargs)
        models.P3Talk.objects.get_or_create(talk=talk)
        return talk


class P3TalkForm(P3TalkFormMixin, cforms.TalkForm):
    type = P3SubmissionForm.base_fields['type']

    class Meta(cforms.TalkForm.Meta):
        exclude = ('duration', 'qa_duration',)

class P3SpeakerForm(cforms.SpeakerForm):
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Short biography (one or two paragraphs). Do not paste your CV'),
        widget=forms.Textarea,)


class FormTicket(forms.ModelForm):
    ticket_name = forms.CharField(max_length=60, required=False, help_text='Name of the attendee')
    days = forms.MultipleChoiceField(label=_('Probable days of attendance'), choices=tuple(), widget=forms.CheckboxSelectMultiple, help_text=_('Please note: The above selection is just for helping the organizers with the catering estimates. It is not binding for you.'),required=False)

    class Meta:
        model = models.TicketConference
        exclude = ('ticket', 'badge_image',)
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
            data = [datetime.datetime.strptime(x, '%Y-%m-%d') for x in [_f for _f in raw if _f]]
        except Exception:
            raise forms.ValidationError('data format not valid')
        conf = cmodels.Conference.objects.current()
        days = []
        for x in data:
            if conf.conference_start <= x.date() <= conf.conference_end:
                days.append(x.strftime('%Y-%m-%d'))
            else:
                raise forms.ValidationError('data not valid')
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
    name = forms.CharField(max_length=60, required=False,
                           help_text='Real name of the person that '
                                     'will attend this specific event.')

    class Meta:
        model = cmodels.Ticket
        fields = ('name',)


class P3ProfileForm(cforms.ProfileForm):
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Short biography (one or two paragraphs). Do not paste your CV'),
        widget=forms.Textarea,
        required=False,)
    tagline = forms.CharField(
        label=_('Tagline'),
        help_text=_('Describe yourself in one line.'),
        required=False,
    )
    interests = cforms.TagField(
        label="Technical interests",
        help_text=_('<p>Please add up to five (5) tags from the shown categories which are relevant to your interests. Only 5 tags will be saved; additional tags are discarded.</p>'),
        widget=cforms.TagWidget,
        required=False)
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
        assert commit, "Postpone P3ProfileForm to work with commit=False"
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
        fields = ('tagline', 'personal_homepage', 'interests', 'twitter',
                  'company', 'company_homepage', 'job_title', 'location',)

    def clean_bio(self):
        return getattr(self.instance.getBio(), 'body', '')

    def save(self, commit=True):
        try:
            oldl = cmodels.AttendeeProfile.objects\
                .values('location')\
                .get(user=self.instance.user_id)['location']
        except (AttributeError, cmodels.AttendeeProfile.DoesNotExist) as e:
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
                country = geocode_country(loc)
                if country:
                    p3p.country = country
                else:
                    # geocode_country() can return None, but the model
                    # does not accept None as input; see #289
                    p3p.country = ''
        else:
            p3p.country = ''

        p3p.save()

        if 'interests' in data:
            valid_tags = cforms.validate_tags(data['interests'])

            p3p.interests.set(*(valid_tags))
        return profile


class P3ProfileBioForm(P3ProfileForm):
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Short biography (one or two paragraphs). Do not paste your CV'),
        widget=forms.Textarea,
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
            ('x', _('no picture')),
            ('g', _('use gravatar')),
            ('u', _('use url')),
            ('f', _('upload file')),
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
        help_text=_('If you opt-in the privacy settings, '
                    'we can send you important communications via SMS.'
                    '<br />Use the international format, '
                    'eg: +99-012-3456789.<br/>This number will <i>never</i> be published.'),
        max_length=30,
        required=False,
    )
    birthday = forms.DateField(
        label=_('Date of birth'),
        help_text=_('We require date of birth for speakers to accommodate for local '
                    'laws regarding minors.<br />'
                    'Format: YYYY-MM-DD<br />This date will <i>never</i> be published.'),
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
                raise forms.ValidationError(_('This field is required for a speaker'))
        return value

    def clean_birthday(self):
        value = self.cleaned_data.get('birthday', '')
        try:
            self.instance.user.speaker
        except (AttributeError, User.DoesNotExist, cmodels.Speaker.DoesNotExist):
            pass
        else:
            if not value:
                raise forms.ValidationError(_('This field is required for a speaker'))
        return value


class P3ProfileEmailContactForm(forms.Form):
    email = forms.EmailField(label="Enter new email")

    def __init__(self, *args, **kw):
        self.user = kw.pop('user', None)
        super(P3ProfileEmailContactForm, self).__init__(*args, **kw)

    def clean_email(self):
        value = self.cleaned_data['email'].strip()
        if self.user:
            if value != self.user.email and User.objects.filter(email__iexact=value).exists():
                raise forms.ValidationError(_('Email already registered'))
        return value


class P3ProfileSpamControlForm(forms.ModelForm):
    spam_recruiting = forms.BooleanField(label=_('I want to receive a few selected job offers through EuroPython.'),
                                         required=False)
    spam_user_message = forms.BooleanField(label=_('I want to receive private messages from other participants.'),
                                           required=False)
    spam_sms = forms.BooleanField(label=_('I want to receive SMS during the conference for main communications.'),
                                  required=False)
    class Meta:
        model = models.P3Profile
        fields = ('spam_recruiting', 'spam_user_message', 'spam_sms')


class P3FormTickets(aforms.FormTickets):
    coupon = forms.CharField(
        label=_('Insert your discount code and save money!'),
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'size': 10}),
    )
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(P3FormTickets, self).__init__(*args, **kwargs)
        # Deleting payment field because I want to delay this choice
        del self.fields['payment']

        # Fields related to hotel reservations behave differently;
        # first of all the can be "multiple" in the sense that for the
        # same fare type (e.g. HB3 - bed in triple room) there could
        # entries for different periods (each entry can specify the
        # number of available beds).
        # Moreover each reservation must specify the "period".

        # These cases will be handled in custom code of clean
        for k in self.fields.keys():
            if k.startswith('H'):
                del self.fields[k]

    def clean_coupon(self):
        data = self.cleaned_data.get('coupon', '').strip()
        if not data:
            return None
        if data[0] == '_':
            raise forms.ValidationError(_('invalid coupon'))
        try:
            coupon = amodels.Coupon.objects.get(
                conference=settings.CONFERENCE_CONFERENCE,
                code__iexact=data)
        except amodels.Coupon.DoesNotExist:
            raise forms.ValidationError(_('invalid coupon'))
        if not coupon.valid(self.user):
            raise forms.ValidationError(_('invalid coupon'))
        return coupon

    def clean(self):
        data = super(P3FormTickets, self).clean()

        company = data.get('order_type') == 'deductible'
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
                data['tickets'].append((Fare.objects.get(conference=settings.CONFERENCE_CONFERENCE,
                                                         code=r['fare']), r))

        if not data['tickets']:
            raise forms.ValidationError('No tickets')

        return data


class P3EventBookingForm(cforms.EventBookingForm):
    def clean_value(self):
        data = super(P3EventBookingForm, self).clean_value()
        if not data:
            return data
        # A "standard" or "daily" ticket is required to book a training
        tt = cmodels.Event.objects\
            .filter(id=self.event)\
            .values('talk__type')[0]['talk__type']
        tickets = dataaccess.all_user_tickets(self.user, conference=settings.CONFERENCE_CONFERENCE)
        for tid, ttype, fcode, complete in tickets:
            if complete and ttype == 'conference'\
                and (fcode[2] in ('S', 'D') or tt != 't'):
                break
        else:
            raise forms.ValidationError('ticket error')

        # No more than one helpdesk per type can be booked
        helpdesk = None
        for t in cmodels.EventTrack.objects\
                    .filter(event=self.event)\
                    .values('track', 'track__track'):
            if 'helpdesk' in t['track__track']:
                helpdesk = t['track']
                break
        if helpdesk:
            custom = cmodels.Event.objects\
                .filter(id=self.event)\
                .values_list('custom', flat=True)[0]
            brothers = cmodels.EventTrack.objects\
                .exclude(event=self.event)\
                .filter(track=helpdesk, event__custom=custom)\
                .values('event')
            booked = cmodels.EventBooking.objects\
                .filter(event__in=brothers, user=self.user)
            if booked.count() > 0:
                raise forms.ValidationError(_('already booked'))
        return data
