# -*- coding: UTF-8 -*-
from django import forms
from django.conf import settings as dsettings
from django.contrib.admin import widgets as admin_widgets
from django.core import mail
from django.forms import widgets
from django.forms.utils import flatatt
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from conference import models
from conference import settings

from p3 import utils as p3utils

from taggit.forms import TagField

import logging

log = logging.getLogger('conference.tags')

### Helpers

def mass_mail(messages, data, addresses, feedback_address):

    # Mass send the emails
    mail.send_mass_mail(messages)

    # Send feedback mail
    ctx = dict(data)
    ctx['addresses'] = '\n'.join(addresses)
    feedback_email = ("""
message sent
-------------------------------
FROM: %(from_)s
SUBJECT: %(subject)s
BODY:
%(body)s
-------------------------------
sent to:
%(addresses)s
""" % ctx)
    mail.send_mail(
        '[%s] feedback mass mailing (admin stats)' % settings.CONFERENCE,
        feedback_email,
        dsettings.DEFAULT_FROM_EMAIL,
        recipient_list=[feedback_address],
     )

###

def validate_tags(tags):
    """
    Returns only tags that are already present in the database
    and limits the results to 5
    """

    valid_tags = models.ConferenceTag.objects.filter(name__in=tags).values_list('name', flat=True)

    tags_limited = valid_tags[:5]

    tags = u', '.join(tags_limited)
    log.debug(u'validated tags: {}'.format(tags))

    return tags_limited


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
        return mark_safe(u'<input%s /><script>setup_tag_field("#%s")</script>' % (flatatt(final_attrs), final_attrs['id']))

# MarkEditWidget we have adapted the code
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

class TalkBaseForm(forms.Form):

    # Talk details
    title = forms.CharField(
        label=_('Title'),
        max_length=80,
        widget=forms.TextInput(attrs={'size': 40}),
        help_text=_('A descriptive, concise title with max 80 chars, e.g. "Big Data Visualization in the Browser with Bokeh"'))
    sub_title = forms.CharField(
        label=_('Subtitle'),
        help_text=_('Juice up your title with max. 100 chars, e.g. "Interactively visualize big data with high performance."'),
        max_length=100,
        widget=forms.TextInput(attrs={'size': 40}),
        required=False)
    abstract = forms.CharField(
        max_length=5000,
        label=_('Abstract (longer version)'),
        help_text=_('<p>Description of the session proposal you are submitting. Be sure to include the goals and any prerequisite required to fully understand it. See the section <em>Submitting Your Talk, Trainings, Helpdesk or Poster</em> of the CFP for further details.</p><p>Suggested size: 1500 chars.</p>'),
        widget=forms.Textarea)
    abstract_short = forms.CharField(
        max_length=500,
        label=_('Abstract (short version)'),
        help_text=_('<p>We need a short description e.g. for YouTube and other distribution channels with limited space for abstracts. <u>You could just use a shorter version of the long abstract</u>.</p><p>Suggested size: <500 chars.</p>'),
        widget=forms.Textarea)
    prerequisites = forms.CharField(
        label=_('Prerequisites for attending the session'),
        help_text=_('What should attendees be familiar with already, important for intermediate and advanced talks.<br />E.g. data visualization basics, data analysis'),
        max_length=150,
        widget=forms.TextInput(attrs={'size': 40}),
        required=False)
    language = forms.TypedChoiceField(
        help_text=_('Select a non-English language only if you are not comfortable in speaking English.'),
        choices=settings.TALK_SUBMISSION_LANGUAGES,
        required=False)

    level = forms.TypedChoiceField(
        label=_('Python Skill level'),
        help_text=_('How experienced should the audience be in python'),
        choices=models.TALK_LEVEL,
        initial=models.TALK_LEVEL.beginner)

    domain_level = forms.TypedChoiceField(
        label=_('Domain Expertise'),
        help_text=_('The domain expertise your audience should have to follow along (e.g. how much should one know about DevOps or Data Science already)'),
        choices=models.TALK_LEVEL,
        initial=models.TALK_LEVEL.beginner)

    # Talk tags
    tags = TagField(
        help_text=_('<p>Please add up to five (5) tags from the shown categories which are relevant to your session proposal. Only 5 tags will be saved; additional tags are discarded.</p>'),
        widget=TagWidget)

    # Details for talk review
    abstract_extra = forms.CharField(
        label=_('Additional information for talk reviewers'),
        help_text=_('<p>Please add anything you may find useful for the review of your session proposal, e.g. references of where you have held talks, blogs, YouTube channels, books you have written, etc. This information will only be shown for talk review purposes.</p>'),
        widget=forms.Textarea,
        required=False)

# This form is used for new talk submissions and only when the speaker
# has not yet submitted another talk; see TalkForm for talk
# editing and additional talks.

class SubmissionForm(forms.Form):
    """
    Submission Form for the first paper, it will contain the fields
    which populates the user profile and the data of the talk,
    only essential data is required.
    """

    # Speaker details
    first_name = forms.CharField(
        label=_('First name'),
        max_length=30)
    last_name = forms.CharField(
        label=_('Last name'),
        max_length=30)
    birthday = forms.DateField(
        label=_('Date of birth'),
        help_text=_('Format: YYYY-MM-DD<br />This date will <strong>never</strong> be published. We require date of birth for speakers to accomodate for laws regarding minors.'),
        input_formats=('%Y-%m-%d',),
        widget=forms.DateInput(attrs={'size': 10, 'maxlength': 10}))
    job_title = forms.CharField(
        label=_('Job title'),
        help_text=_('eg: student, developer, CTO, js ninja, BDFL'),
        max_length=50,
        required=False,)
    phone = forms.CharField(
        help_text=_('We require a mobile number for all speakers for important last minutes contacts.<br />Use the international format, eg: +39-055-123456.<br />This number will <strong>never</strong> be published.'),
        max_length=30)
    company = forms.CharField(
        label=_('Your company'),
        max_length=50,
        required=False)
    company_homepage = forms.URLField(
        label=_('Company homepage'),
        required=False)
    bio = forms.CharField(
        label=_('Compact biography'),
        help_text=_('Please enter a short biography (one or two paragraphs) <br />Do not paste your CV!'),
        widget=forms.Textarea())

    # Talk details
    title = TalkBaseForm.base_fields['title']
    sub_title = TalkBaseForm.base_fields['sub_title']
    abstract = TalkBaseForm.base_fields['abstract']
    abstract_short = TalkBaseForm.base_fields['abstract_short']
    prerequisites = TalkBaseForm.base_fields['prerequisites']
    language = TalkBaseForm.base_fields['language']
    level = TalkBaseForm.base_fields['level']
    domain_level = TalkBaseForm.base_fields['level']
    tags = TalkBaseForm.base_fields['tags']
    abstract_extra = TalkBaseForm.base_fields['abstract_extra']

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
            if profile.birthday is None:
                birthday_value = None
            else:
                birthday_value = profile.birthday.strftime('%Y-%m-%d')

            data.update({
                'phone': profile.phone,
                'birthday': birthday_value,
                'job_title': profile.job_title,
                'company': profile.company,
                'company_homepage': profile.company_homepage,
                'bio': getattr(profile.getBio(), 'body', ''),
            })
        data.update(kwargs.get('initial', {}))
        kwargs['initial'] = data
        super(SubmissionForm, self).__init__(*args, **kwargs)
        self.user = user

    #@transaction.atomic
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
            title=data['title'],
            sub_title=data['sub_title'],
            prerequisites=data['prerequisites'],
            abstract_short=data['abstract_short'],
            abstract_extra=data['abstract_extra'],conference=settings.CONFERENCE,
            speaker=speaker,
            status='proposed',
            language=data['language'],
            domain=data['domain'],
            domain_level=data['domain_level'],
            level=data['level'],
            type=data['type']
        )

        talk.save()
        talk.setAbstract(data['abstract'])

        if 'tags' in data:
            valid_tags = validate_tags(data['tags'])

            talk.tags.set(*(valid_tags))

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

_abstract = models.Talk._meta.get_field_by_name('abstracts')[0]

# This form is used in case the speaker has already proposed a talk
# and for editing talks

class TalkForm(forms.ModelForm):

    # Talk details
    title = TalkBaseForm.base_fields['title']
    sub_title = TalkBaseForm.base_fields['sub_title']
    abstract = TalkBaseForm.base_fields['abstract']
    abstract_short = TalkBaseForm.base_fields['abstract_short']
    prerequisites = TalkBaseForm.base_fields['prerequisites']
    language = TalkBaseForm.base_fields['language']
    level = TalkBaseForm.base_fields['level']
    tags = TalkBaseForm.base_fields['tags']
    abstract_extra = TalkBaseForm.base_fields['abstract_extra']

    class Meta:
        model = models.Talk
        fields = ('title', 'sub_title','prerequisites', 'abstract_short', 'abstract_extra', 'type', 'language', 'level', 'slides', 'teaser_video', 'tags')
        widgets = {
            'tags': TagWidget,
        }

    def __init__(self, *args, **kw):
        if kw.get('instance'):
            o = kw['instance']
            initial = kw.get('initial', {})
            data = {}
            abstract = o.getAbstract()
            if abstract:
                data['abstract'] = abstract.body
            data.update(initial)
            kw['initial'] = data
        super(TalkForm, self).__init__(*args, **kw)

    def save(self, commit=True, speaker=None):
        assert commit, "commit==False not supported yet"
        data = self.cleaned_data
        pk = self.instance.pk

        tags = None

        if 'tags' in self.cleaned_data:
            tags = self.cleaned_data['tags']
            del self.cleaned_data['tags']

        if not pk:
            assert speaker is not None
            self.instance = models.Talk.objects.createFromTitle(
                title=data['title'],
                sub_title=data['sub_title'],
                prerequisites=data['prerequisites'],
                abstract_short=data['abstract_short'],
                abstract_extra=data['abstract_extra'],
                domain=data['domain'],
                domain_level=data['domain_level'],
                conference=settings.CONFERENCE,
                speaker=speaker,
                status='proposed',
                language=data['language'],
                level=data['level'],
                type=data['type']
            )
        talk = super(TalkForm, self).save(commit=commit)
        talk.setAbstract(data['abstract'])

        if tags:
            valid_tags = validate_tags(tags)

            talk.tags.set(*(valid_tags))

        if not pk:
            from conference.listeners import new_paper_submission
            new_paper_submission.send(sender=speaker, talk=self.instance)
        return talk

del _abstract

from tagging.models import TaggedItem
from tagging.utils import parse_tag_input

class TrackForm(forms.ModelForm):
    class Meta:
        model = models.Track
        exclude = ('schedule', 'track',)

class EventForm(forms.ModelForm):
    event_tracks = forms.ModelMultipleChoiceField(queryset=models.Track.objects.all())

    class Meta:
        model = models.Event
        exclude = ('schedule', 'tracks')

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        if self.instance.id:
            self.fields['talk'].queryset = models.Talk.objects\
                .filter(conference=self.instance.schedule.conference)
            self.fields['event_tracks'].queryset = models.Track.objects\
                .filter(schedule__conference=self.instance.schedule.conference)

    def clean(self):
        data = super(EventForm, self).clean()
        if not data['talk'] and not data['custom']:
            raise forms.ValidationError('set the talk or the custom text')
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

class EventBookingForm(forms.Form):
    value = forms.BooleanField(required=False)

    def __init__(self, event, user, *args, **kwargs):
        super(EventBookingForm, self).__init__(*args, **kwargs)
        self.event = event
        self.user = user

    def clean_value(self):
        data = self.cleaned_data.get('value', False)
        if data and not models.EventBooking.objects.booking_available(self.event, self.user):
            raise forms.ValidationError('sold out')
        return data

class AdminSendMailForm(forms.Form):
    """
    This form is used by the admin:
        * statistics for the sold tickets
        * allow to send a mail to a group of users
    """
    from_ = forms.EmailField(max_length=50, initial=dsettings.DEFAULT_FROM_EMAIL)
    subject = forms.CharField(max_length=200)
    body = forms.CharField(widget=forms.Textarea)
    send_email = forms.BooleanField(required=False)

    def __init__(self, *args, **kw):
        real = kw.pop('real_usage', True)
        super(AdminSendMailForm, self).__init__(*args, **kw)
        if real:
            self.fields['send_email'].required = True

    def load_emails(self):
        if not settings.ADMIN_TICKETS_STATS_EMAIL_LOG:
            return []
        try:
            f = file(settings.ADMIN_TICKETS_STATS_EMAIL_LOG)
        except:
            return []
        output = []
        while True:
            try:
                msg = {
                    'from_': eval(f.readline()).strip(),
                    'subject': eval(f.readline()).strip(),
                    'body': eval(f.readline()).strip(),
                }
            except:
                break
            f.readline()
            if msg['from_']:
                output.append(msg)
            else:
                break
        return reversed(output)

    def save_email(self):
        if not settings.ADMIN_TICKETS_STATS_EMAIL_LOG:
            return False
        data = self.cleaned_data
        with file(settings.ADMIN_TICKETS_STATS_EMAIL_LOG, 'a') as f:
            f.write('%s\n' % repr(data['from_']))
            f.write('%s\n' % repr(data['subject']))
            f.write('%s\n' % repr(data['body']))
            f.write('------------------------------------------\n')
        return True

    def preview(self, *uids):
        from django.template import Template, Context
        from django.contrib.auth.models import User

        data = self.cleaned_data

        if settings.ADMIN_TICKETS_STATS_EMAIL_LOAD_LIBRARY:
            libs = '{%% load %s %%}' % ' '.join(settings.ADMIN_TICKETS_STATS_EMAIL_LOAD_LIBRARY)
        else:
            libs = ''
        tSubject = Template(libs + data['subject'])
        tBody = Template(libs + data['body'])

        conf = models.Conference.objects.current()

        output = []
        for u in User.objects.filter(id__in=uids):
            ctx = Context({
                'user': u,
                'conf': conf,
                'tickets': p3utils.get_tickets_assigned_to(u),
            })
            output.append((
                tSubject.render(ctx),
                tBody.render(ctx),
                u,
            ))
        return output

    def send_emails(self, uids, feedback_address):
        messages = []
        addresses = []
        data = self.cleaned_data

        # Make sure we don't send duplicate emails to the same uid
        uids = list(set(uids))

        # Prepare emails
        for sbj, body, user in self.preview(*uids):
            messages.append((sbj, body, data['from_'], [user.email]))
            addresses.append('"%s %s" - %s' % (user.first_name, user.last_name, user.email))

        # Mass send the emails (in a separate process)
        import multiprocessing
        process = multiprocessing.Process(
            target=mass_mail,
            args=(messages, data, addresses, feedback_address))
        process.daemon=True
        process.start()
        # Let it run until completion without joining it again
        process = None
        return len(messages)

class AttendeeLinkDescriptionForm(forms.Form):
    message = forms.CharField(label='A note to yourself (when you met this persone, why you want to stay in touch)', widget=forms.Textarea)

# -- Custom Option Form used for Talk Voting Filters
class OptionForm(forms.Form):
    abstracts = forms.ChoiceField(
        choices=(('not-voted', 'To be voted'), ('all', 'All'),),
        required=False,
        initial='not-voted',
        widget=forms.RadioSelect(renderer=PseudoRadioRenderer),
    )
    talk_type = forms.ChoiceField(
        choices=settings.TALK_TYPES_TO_BE_VOTED,
        required=False,
        initial='all',
        widget=forms.RadioSelect(renderer=PseudoRadioRenderer),
    )
    language = forms.ChoiceField(
        choices=(('all', 'All'),) + tuple(settings.TALK_SUBMISSION_LANGUAGES),
        required=False,
        initial='all',
        widget=forms.RadioSelect(renderer=PseudoRadioRenderer),
    )
    order = forms.ChoiceField(
        choices=(('vote', 'Vote'), ('speaker', 'Speaker name'),),
        required=False,
        initial='vote',
        widget=forms.RadioSelect(renderer=PseudoRadioRenderer),
    )
    tags = TagField(
        required=False,
        widget=ReadonlyTagWidget(),
    )
