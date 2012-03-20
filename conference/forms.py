# -*- coding: UTF-8 -*-
from django import forms
from django.contrib.admin import widgets as admin_widgets
from django.db import transaction
from django.forms import widgets
from django.forms.util import flatatt
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from conference import models
from conference import settings

from taggit.forms import TagField

class TagWidget(widgets.TextInput):
    def _media(self):
        return forms.Media(
            js=('conference/tag-it/js/tag-it.js',),
            css={'all': ('conference/tag-it/css/jquery.tagit.css',)},
        )
    media = property(_media)

    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        else:
            if not isinstance(value, basestring):
                names = []
                for v in value:
                    if isinstance(v, basestring):
                        names.append(v)
                    elif isinstance(v, models.ConferenceTag):
                        names.append(v.name)
                    else:
                        names.append(v.tag.name)
                value = ','.join(names)
        final_attrs = self.build_attrs(attrs, type='text', name=name)
        final_attrs['class'] = (final_attrs.get('class', '') + ' tag-field').strip()
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_unicode(self._format_value(value))
        return mark_safe(u'<input%s />' % flatatt(final_attrs))

class ReadonlyTagWidget(widgets.TextInput):
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        else:
            if not isinstance(value, basestring):
                names = []
                for v in value:
                    if isinstance(v, basestring):
                        names.append(v)
                    elif isinstance(v, models.ConferenceTag):
                        names.append(v.name)
                    else:
                        names.append(v.tag.name)
                value = ','.join(names)
        final_attrs = self.build_attrs(attrs, type='text', name=name)
        final_attrs['class'] = (final_attrs.get('class', '') + ' readonly-tag-field').strip()
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_unicode(self._format_value(value))
        return mark_safe(u'<input%s />' % flatatt(final_attrs))

# MarkEditWidget adattameto del codice di esempio presente in 
# http://tstone.github.com/jquery-markedit/

class MarkEditWidget(forms.Textarea):
    class Media:
        css = {
            'all': ('conference/jquery-markedit/jquery.markedit.css',),
        }
        js =  (
            'conference/jquery-markedit/showdown.js',
            'conference/jquery-markedit/jquery.markedit.js',
        )

    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        else:
            attrs = dict(attrs)
        attrs['class'] = (attrs.get('class', '') + ' markedit-widget').strip()
        return super(MarkEditWidget, self).render(name, value, attrs)

class AdminMarkEdit(admin_widgets.AdminTextareaWidget, MarkEditWidget):
    pass

class PseudoRadioWidget(forms.TextInput):
    def render(self, name, value, attrs=None):
        pass

class PseudoRadioRenderer(forms.widgets.RadioFieldRenderer):
    def render(self):
        h = '<div class="%(class)s" data-value="%(value)s"><span>%(label)s</span></div>'
        choiches = []
        for w in self:
            p = {
                'class': 'pseudo-radio',
                'value': w.choice_value,
                'label': w.choice_label,
            }
            if w.is_checked():
                p['class'] += ' checked'
            choiches.append(h % p)
        output = '<div class="pseudo-radio-field"><input type="hidden" name="%s" value="%s" />%s</div>'
        return mark_safe(output % (self.name, self.value, ''.join(choiches)))

class SubmissionForm(forms.Form):
    """
    Form per la submission del primo paper; include campi che andranno a
    popolare sia il profilo dello speaker che i dati del talk. Vengono
    richiesti i soli dati essenziali.
    """
    first_name = forms.CharField(
        label=_('First name'),
        max_length=30,)
    last_name = forms.CharField(
        label=_('Last name'),
        max_length=30,)
    birthday = forms.DateField(
        label=_('Date of birth'),
        help_text=_('We require date of birth for speakers to accomodate for Italian laws regarding minors.<br />Format: YYYY-MM-DD<br />This date will <strong>never</strong> be published.'),
        input_formats=('%Y-%m-%d',),
        widget=forms.DateInput(attrs={'size': 10, 'maxlength': 10}),
    )
    job_title = forms.CharField(
        label=_('Job title'),
        help_text=_('eg: student, developer, CTO, js ninja, BDFL'),
        max_length=50,
        required=False,)
    phone = forms.CharField(
        help_text=_('We require a mobile number for all speakers for important last minutes contacts.<br />Use the international format, eg: +39-055-123456.<br />This number will <strong>never</strong> be published.'),
        max_length=30)
    company = forms.CharField(label=_('Your company'), max_length=50, required=False)
    company_homepage = forms.URLField(label=_('Company homepage'), required=False)
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=forms.Textarea(),)

    title = forms.CharField(label=_('Talk title'), max_length=100, widget=forms.TextInput(attrs={'size': 40}))
    type = forms.TypedChoiceField(
        label=_('Talk Type'),
        help_text=_('Talk Type description'),
        choices=models.TALK_TYPE,
        initial='s',
        required=True,)
    duration = forms.TypedChoiceField(
        label=_('Suggested duration'),
        help_text=_('This is the <b>net duration</b> of the talk, excluding Q&A'),
        choices=models.TALK_DURATION,
        coerce=int,
        initial='30',)
    language = forms.TypedChoiceField(
        help_text=_('Select Italian only if you are not comfortable in speaking English.'),
        choices=models.TALK_LANGUAGES,
        initial='en',)
    level = forms.TypedChoiceField(label=_('Audience level'), choices=models.TALK_LEVEL, initial='beginner')
    abstract = forms.CharField(
        max_length=5000,
        label=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'),
        widget=forms.Textarea(),)
    tags = TagField(widget=TagWidget)

    def __init__(self, user, *args, **kwargs):
        try:
            profile = user.attendeeprofile
        except models.AttendeeProfile.DoesNotExist:
            profile = None
        data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        if profile:
            data.update({
                'phone': profile.phone,
                'birthday': profile.birthday,
                'job_title': profile.job_title,
                'company': profile.company,
                'company_homepage': profile.company_homepage,
                'bio': getattr(profile.getBio(), 'body', ''),
            })
        data.update(kwargs.get('initial', {}))
        kwargs['initial'] = data
        super(SubmissionForm, self).__init__(*args, **kwargs)
        self.user = user

    @transaction.commit_on_success
    def save(self):
        data = self.cleaned_data

        user = self.user
        user.first_name = data['first_name'].strip()
        user.last_name = data['last_name'].strip()
        user.save()

        profile = models.AttendeeProfile.objects.getOrCreateForUser(user)
        profile.phone = data['phone']
        profile.birthday = data['birthday']
        profile.job_title = data['job_title']
        profile.company = data['company']
        profile.company_homepage = data['company_homepage']
        profile.save()
        profile.setBio(data['bio'])

        try:
            speaker = user.speaker
        except models.Speaker.DoesNotExist:
            speaker = models.Speaker(user=user)
            speaker.save()

        talk = models.Talk.objects.createFromTitle(
            title=data['title'], conference=settings.CONFERENCE, speaker=speaker,
            status='proposed', duration=data['duration'], language=data['language'],
            level=data['level'], type=data['type'],
        )
        talk.setAbstract(data['abstract'])
        talk.tags.set(*data['tags'])

        from conference.listeners import new_paper_submission
        new_paper_submission.send(sender=speaker, talk=talk)

        return talk

class SpeakerForm(forms.Form):
    activity = forms.CharField(
        label=_('Job title'),
        help_text=_('eg: student, developer, CTO, js ninja, BDFL'),
        max_length=50,
        required=False,)
    activity_homepage = forms.URLField(label=_('Personal homepage'), required=False)
    company = forms.CharField(label=_('Your company'), max_length=50, required=False)
    company_homepage = forms.URLField(label=_('Company homepage'), required=False)
    industry = forms.CharField(max_length=50, required=False)
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=forms.Textarea(),)
    ad_hoc_description = forms.CharField(label=_('Presentation'), required=False)

class TalkForm(forms.Form):
    title = forms.CharField(label=_('Talk title'), max_length=100, widget=forms.TextInput(attrs={'size': 40}))
    duration = forms.TypedChoiceField(
        label=_('Suggested duration'),
        help_text=_('This is the <b>net duration</b> of the talk, excluding Q&A'),
        choices=models.TALK_DURATION,
        coerce=int,
        initial='30',)
    type = forms.TypedChoiceField(
        label=_('Talk Type'),
        choices=models.TALK_TYPE,
        initial='s',
        required=True,)
    language = forms.TypedChoiceField(choices=models.TALK_LANGUAGES, initial='en')
    level = forms.TypedChoiceField(label=_('Audience level'), choices=models.TALK_LEVEL, initial='beginner')
    slides = forms.FileField(required=False)
    abstract = forms.CharField(
        max_length=5000,
        label=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'),
        widget=forms.Textarea(),)
    teaser_video = forms.URLField(
        label=_('Teaser video'),
        help_text=_('Insert the url for your teaser video'),
        required=False,
    )
    tags = TagField(widget=TagWidget)

    def __init__(self, instance=None, *args, **kwargs):
        if instance:
            data = {
                'type': instance.type,
                'title': instance.title,
                'duration': instance.duration,
                'language': instance.language,
                'level': instance.level,
                'abstract': getattr(instance.getAbstract(), 'body', ''),
                'teaser_video': instance.teaser_video,
                'tags': instance.tags.all(),
            }
            data.update(kwargs.get('initial', {}))
            kwargs['initial'] = data
        super(TalkForm, self).__init__(*args, **kwargs)
        self.instance = instance

    @transaction.commit_on_success
    def save(self, speaker=None):
        data = self.cleaned_data
        o = self.instance
        if o is None:
            assert speaker is not None
            o = models.Talk.objects.createFromTitle(
                title=data['title'], conference=settings.CONFERENCE, speaker=speaker,
                status='proposed', duration=data['duration'], language=data['language'],
                level=data['level'],
            )
        else:
            o.title = data['title']
            o.duration = data['duration']
            o.language = data['language']
            o.level = data['level']

        o.type = data['type']
        o.teaser_video = data['teaser_video']
        if data['slides']:
            o.slides = data['slides']
        o.save()
        o.setAbstract(data['abstract'])
        o.tags.set(*data['tags'])

        return o

from tagging.models import TaggedItem
from tagging.utils import parse_tag_input

class EventForm(forms.ModelForm):
    class Meta:
        model = models.Event
        exclude = ('schedule',)

    def __init__(self, *args, **kwargs):
        i = kwargs.get('instance', None)
        if not i:
            self.schedule = kwargs.pop('schedule')
        else:
            self.schedule = i.schedule
        super(EventForm, self).__init__(*args, **kwargs)
        self.fields['talk'].queryset = models.Talk.objects\
            .filter(conference=self.schedule.conference)

    def clean(self):
        data = super(EventForm, self).clean()
        if not data['talk'] and not data['custom']:
            raise forms.ValidationError('set the talk or the custom text')

        schedule_tracks = set()
        indoor_tracks = set()
        for t in self.schedule.track_set.all():
            schedule_tracks.add(t.track)
            if not t.outdoor:
                indoor_tracks.add(t.track)

        tracks = set(parse_tag_input(data['track']))
        if 'special' in tracks or 'break' in tracks:
            if not tracks & schedule_tracks:
                tracks |= indoor_tracks
        for t in schedule_tracks:
            conflicts = set(TaggedItem.objects.get_by_model(models.Event.objects.filter(schedule=self.schedule, start_time=data['start_time']), t))
            if self.instance:
                conflicts = conflicts - set((self.instance,))
            if conflicts:
                raise forms.ValidationError('conflicts on "%s"' % data['start_time'])

        return data

class ProfileForm(forms.ModelForm):
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs). Do not paste your CV!'),
        widget=forms.Textarea(),
        required=False,)

    class Meta:
        model = models.AttendeeProfile
        exclude = ('user', 'slug',)

    def __init__(self, *args, **kwargs):
        i = kwargs.get('instance')
        if i:
           initial = kwargs.get('initial', {})
           initial['bio'] = getattr(i.getBio(), 'body', '')
           kwargs['initial'] = initial
        super(ProfileForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        profile = super(ProfileForm, self).save(commit)
        profile.setBio(self.cleaned_data.get('bio', ''))
        return profile
