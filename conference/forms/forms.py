import logging

from django import forms
from django.conf import settings
from django.core import mail
from django.forms import widgets
from django.forms.utils import flatatt
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from taggit.forms import TagField

from p3 import utils as p3utils
from conference import models

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
        '[%s] feedback mass mailing (admin stats)' % settings.CONFERENCE_CONFERENCE,
        feedback_email,
        settings.DEFAULT_FROM_EMAIL,
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

    tags = ', '.join(tags_limited)
    log.debug('validated tags: {}'.format(tags))

    return tags_limited


class TagWidget(widgets.TextInput):
    def _media(self):
        return forms.Media(
            js=('conference/tag-it/js/tag-it.js',),
            css={'all': ('conference/tag-it/css/jquery.tagit.css',)},
        )
    media = property(_media)

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = ''
        else:
            if not isinstance(value, str):
                names = []
                for v in value:
                    if isinstance(v, str):
                        names.append(v)
                    elif isinstance(v, models.ConferenceTag):
                        names.append(v.name)
                    else:
                        names.append(v.tag.name)
                value = ','.join(names)
        final_attrs = self.build_attrs(attrs, extra_attrs=dict(type='text', name=name))
        final_attrs['class'] = (final_attrs.get('class', '') + ' tag-field').strip()
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_text(self._format_value(value))
        return mark_safe('<input%s />' % flatatt(final_attrs))


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
        choices=settings.CONFERENCE_TALK_SUBMISSION_LANGUAGES,
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
        super().__init__(*args, **kwargs)
        if self.instance.id:
            self.fields['talk'].queryset = models.Talk.objects\
                .filter(conference=self.instance.schedule.conference)
            self.fields['event_tracks'].queryset = models.Track.objects\
                .filter(schedule__conference=self.instance.schedule.conference)

    def clean(self):
        data = super().clean()
        if not data['talk'] and not data['custom']:
            raise forms.ValidationError('set the talk or the custom text')
        return data


class AdminSendMailForm(forms.Form):
    """
    This form is used by the admin:
        * statistics for the sold tickets
        * allow to send a mail to a group of users
    """
    from_ = forms.EmailField(max_length=50, initial=settings.DEFAULT_FROM_EMAIL)
    subject = forms.CharField(max_length=200)
    body = forms.CharField(widget=forms.Textarea)
    send_email = forms.BooleanField(required=False)

    def __init__(self, *args, **kw):
        real = kw.pop('real_usage', True)
        super().__init__(*args, **kw)

    def load_emails(self):
        if not settings.CONFERENCE_ADMIN_TICKETS_STATS_EMAIL_LOG:
            return []

        output = []
        try:
            with open(settings.CONFERENCE_ADMIN_TICKETS_STATS_EMAIL_LOG, 'r') as email_log_file:
                while True:
                    try:
                        msg = {
                            'from_': eval(email_log_file.readline()).strip(),
                            'subject': eval(email_log_file.readline()).strip(),
                            'body': eval(email_log_file.readline()).strip(),
                        }
                    except:
                        break
                    email_log_file.readline()
                    if msg['from_']:
                        output.append(msg)
                    else:
                        break
        except:
            return []

        return reversed(output)

    def save_email(self):
        if not settings.CONFERENCE_ADMIN_TICKETS_STATS_EMAIL_LOG:
            return False
        data = self.cleaned_data
        with open(settings.CONFERENCE_ADMIN_TICKETS_STATS_EMAIL_LOG, 'a') as email_log_file:
            email_log_file.write('%s\n' % repr(data['from_']))
            email_log_file.write('%s\n' % repr(data['subject']))
            email_log_file.write('%s\n' % repr(data['body']))
            email_log_file.write('------------------------------------------\n')
        return True

    def preview(self, *uids):
        from django.template import Template, Context
        from django.contrib.auth.models import User

        data = self.cleaned_data

        if settings.CONFERENCE_ADMIN_TICKETS_STATS_EMAIL_LOAD_LIBRARY:
            libs = '{%% load %s %%}' % ' '.join(settings.CONFERENCE_ADMIN_TICKETS_STATS_EMAIL_LOAD_LIBRARY)
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
