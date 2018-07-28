# -*- coding: UTF-8 -*-
import datetime
import os
import os.path
import subprocess
from collections import defaultdict

from django.conf import settings as dsettings
from django.core import exceptions
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models
from django.db import transaction
from django.db.models.query import QuerySet
from django.db.models.signals import post_save
from django.template.defaultfilters import slugify
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext as _

from common.django_urls import UrlMixin
from model_utils import Choices
from model_utils.models import TimeStampedModel

import tagging
from tagging.fields import TagField

import conference
import conference.gmap
from . import settings, signals

from taggit.models import TagBase, GenericTaggedItemBase, ItemBase
from taggit.managers import TaggableManager

import logging

log = logging.getLogger('conference.tags')


CURRENT_CONFERENCE_CACHE_KEY = 'CONFERENCE_CURRENT'


# ConferenceTag and ConferenceTaggedItem are used to create a "namesapce"
# for the related tags to a conference.
class ConferenceTagManager(models.Manager):
    def get_queryset(self):
        return self._QuerySet(self.model)

    def __getattr__(self, name):
        return getattr(self.all(), name)

    class _QuerySet(QuerySet):
        def annotate_with_usage(self):
            return self\
                .annotate(usage=models.Count('conference_conferencetaggeditem_items'))
        def order_by_usage(self, asc=False):
            key = 'usage' if asc else '-usage'
            return self.annotate_with_usage().order_by(key)


class ConferenceTag(TagBase):
    objects = ConferenceTagManager()
    category = models.CharField(max_length=50, default='', blank=True)

    def save(self, **kw):
        if not self.pk:
            try:
                c = ConferenceTag.objects.get(name__iexact=self.name)
            except ConferenceTag.DoesNotExist:
                pass
            else:
                self.pk = c.pk
                return
        return super(ConferenceTag, self).save(**kw)

class ConferenceTaggedItem(GenericTaggedItemBase, ItemBase):
    tag = models.ForeignKey(ConferenceTag, related_name="%(app_label)s_%(class)s_items")

    class Meta:
        verbose_name = _("Tagged Item")
        verbose_name_plural = _("Tagged Items")


class ConferenceManager(models.Manager):
    def current(self):
        data = cache.get(CURRENT_CONFERENCE_CACHE_KEY)
        a_week = 60 * 60 * 24 * 7

        if data is None:
            data = self.get(code=dsettings.CONFERENCE_CONFERENCE)
            cache.set(CURRENT_CONFERENCE_CACHE_KEY, data, a_week)

        return data

    @classmethod
    def clear_cache(cls, sender, **kwargs):
        cache.delete(CURRENT_CONFERENCE_CACHE_KEY)


class Conference(models.Model):
    code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100)
    cfp_start = models.DateField(null=True, blank=True)
    cfp_end = models.DateField(null=True, blank=True)
    conference_start = models.DateField(null=True, blank=True)
    conference_end = models.DateField(null=True, blank=True)
    voting_start = models.DateField(null=True, blank=True)
    voting_end = models.DateField(null=True, blank=True)

    objects = ConferenceManager()

    def __unicode__(self):
        return self.code

    def save(self, *args, **kwargs):
        """
        Every time we make a change to any Conference, we should clear the
        CONFERENCE_CURRENT cache.
        """
        cache.delete(CURRENT_CONFERENCE_CACHE_KEY)
        super(Conference, self).save(*args, **kwargs)

    def days(self):
        output = []
        if self.conference_start and self.conference_end:
            d = self.conference_start
            step = datetime.timedelta(days=1)
            while d<= self.conference_end:
                output.append(d)
                d += step
        return output

    def clean(self):
        if self.conference_start and self.conference_end:
            if self.conference_start > self.conference_end:
                raise exceptions.ValidationError('Conference end must be > of conference start')
        if self.cfp_start and self.cfp_end:
            if self.cfp_start > self.cfp_end:
                raise exceptions.ValidationError('Cfp end must be > of cfp start')
        if self.voting_start and self.voting_end:
            if self.voting_start > self.voting_end:
                raise exceptions.ValidationError('Voting end must be > of voting start')

    def cfp(self):
        today = datetime.date.today()
        try:
            return self.cfp_start <= today <= self.cfp_end
        except TypeError:
            # there is no date, return False
            return False

    def voting(self):
        today = datetime.date.today()
        try:
            return self.voting_start <= today <= self.voting_end
        except TypeError:
            # there is no date, return False
            return False

    def conference(self):
        today = datetime.date.today()
        return self.conference_start <= today <= self.conference_end

post_save.connect(ConferenceManager.clear_cache, sender=Conference)

class DeadlineManager(models.Manager):
    def valid_news(self):
        today = datetime.date.today()
        return self.all().filter(date__gte = today)

class Deadline(models.Model):
    """
    Deadline for the PyCon
    """
    date = models.DateField()

    objects = DeadlineManager()

    def __unicode__(self):
        return "deadline: %s" % (self.date, )

    class Meta:
        ordering = ['date']

    def isExpired(self):
       today = datetime.date.today()
       return today > self.date

    def content(self, lang, fallback=True):
        """
        Return the dead line content in the specified language.
        """
        contents = dict((c.language, c) for c in self.deadlinecontent_set.exclude(body=''))
        if not contents:
            raise DeadlineContent.DoesNotExist()
        try:
            return contents[lang]
        except KeyError:
            if not fallback:
                raise DeadlineContent.DoesNotExist()

        return contents.values()[0]

class DeadlineContent(models.Model):
    """
    Content of a deadline.
    """
    deadline = models.ForeignKey(Deadline)
    language = models.CharField(max_length=3)
    headline = models.CharField(max_length=200)
    body = models.TextField()

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import (
    GenericForeignKey,
    GenericRelation
)


class MultilingualContentManager(models.Manager):
    def setContent(self, object, content, language, body):
        if language is None:
            language = dsettings.LANGUAGE_CODE.split('-', 1)[0]
        object_type = ContentType.objects.get_for_model(object)
        try:
            mc = self.get(content_type=object_type, object_id=object.pk, content=content, language=language)
        except MultilingualContent.DoesNotExist:
            mc = MultilingualContent(content_object=object)
            mc.content = content
            mc.language = language
        mc.body = body
        mc.save()

    def getContent(self, object, content, language):
        if language is None:
            language = dsettings.LANGUAGE_CODE.split('-', 1)[0]
        object_type = ContentType.objects.get_for_model(object)
        records = dict(
            (x.language, x)
            for x in self.exclude(body='').filter(content_type=object_type, object_id=object.pk, content=content)
        )
        try:
            return records[language]
        except KeyError:
            if not records:
                return None
            else:
                return records.get(dsettings.LANGUAGE_CODE, records.values()[0])

class MultilingualContent(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    language = models.CharField(max_length = 3)
    content = models.CharField(max_length = 20)
    body = models.TextField()

    objects = MultilingualContentManager()


@deconstructible
class _fs_upload_to(object):
    """Deconstructible class to avoid django migrations' limitations on
    python2. See https://code.djangoproject.com/ticket/22999 """

    def __init__(self, subdir, attr=None, package='conference'):
        self.subdir = subdir
        self.attr = attr if attr is not None else 'slug'
        self.package = package

    def __call__(self, instance, filename):
        fpath = os.path.join(
            self.package,
            self.subdir,
            '%s%s' % (getattr(instance, self.attr), os.path.splitext(filename)[1].lower())
        )

        ipath = os.path.join(dsettings.MEDIA_ROOT, fpath)

        if os.path.exists(ipath):
            os.unlink(ipath)

        return fpath

def postSaveResizeImageHandler(sender, **kwargs):
    tool = os.path.join(os.path.dirname(conference.__file__), 'utils', 'resize_image.py')
    null = open('/dev/null')
    p = subprocess.Popen(
        [tool, settings.STUFF_DIR],
        close_fds=True, stdin=null, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.communicate()

class AttendeeProfileManager(models.Manager):
    def findSlugForUser(self, user):
        name = '%s %s' % (user.first_name, user.last_name)
        slug = slugify(name)

        rows = self.filter(models.Q(slug=slug) | models.Q(slug__startswith=slug + '-'))\
            .values_list('slug', flat=True)
        last = None
        for r in rows:
            try:
                counter = int(r.rsplit('-', 1)[1])
            except (ValueError, IndexError):
                if last is None:
                    # The protection from slug like "str-str-str"
                    last = 0
                continue
            if counter > last:
                last = counter

        if last is not None:
            slug = '%s-%d' % (slug, last+1)
        elif not slug:
            # if there is no slug, because the firstname or the lastname are empties,
            # we will return '-1'
            slug = '-1'
        return slug


    def randomUUID(self, length=6):
        import string
        import random
        return ''.join(random.sample(string.letters + string.digits, length))

    # TODO: Use the savepoint.
    # Remember that, at least up to 1.4 django, SQLite backend does not support
    # savepoint. Then you must move from cursor.execute(); if you ever pass to PostgreSQL
    # Rememeber  to roll back the savepoint in the except (or set the autocommit)
    def getOrCreateForUser(self, user):
        """
        Returns or create the associated profile
        """
        try:
            p = AttendeeProfile.objects.get(user=user)
        except AttendeeProfile.DoesNotExist:
            p = AttendeeProfile(user=user)
        else:
            return p

        from django.db import IntegrityError
        slug = None
        uuid = None
        while True:
            if slug is None:
                slug = self.findSlugForUser(user)
            if uuid is None:
                uuid = self.randomUUID()

            p.slug = slug
            p.uuid = uuid
            try:
                p.save()
            except IntegrityError as e:
                msg = str(e)
                if 'uuid' in msg:
                    uuid = None
                elif 'slug' in msg:
                    slug = None
                else:
                    raise
            else:
                break
        return p

ATTENDEEPROFILE_VISIBILITY = (
    ('x', 'Private (disabled)'),
    ('m', 'Participants only'),
    ('p', 'Public'),
)
class AttendeeProfile(models.Model):
    """
    It's the profile of a participant (including the speaker) at the conference, there is a connection
    to the auth.User via a ForeignKey.
    """
    user = models.OneToOneField('auth.User', primary_key=True)
    slug = models.SlugField(unique=True)
    uuid = models.CharField(max_length=6, unique=True)

    image = models.ImageField(upload_to=_fs_upload_to('profile'), blank=True)
    birthday = models.DateField(_('Birthday'), null=True, blank=True)
    phone = models.CharField(
        _('Phone'),
        max_length=30, blank=True,
        help_text=_('Enter a phone number where we can contact you in case of administrative issues.<br />Use the international format, eg: +39-055-123456'),
    )

    personal_homepage = models.URLField(_('Personal homepage'), blank=True)
    company = models.CharField(_('Company'), max_length=50, blank=True)
    company_homepage = models.URLField(_('Company homepage'), blank=True)
    job_title = models.CharField(_('Job title'), max_length=50, blank=True)

    location = models.CharField(_('Location'), max_length=100, blank=True)
    bios = GenericRelation(MultilingualContent)

    visibility = models.CharField(max_length=1, choices=ATTENDEEPROFILE_VISIBILITY, default='x')

    objects = AttendeeProfileManager()

    def __unicode__(self):
        return self.slug

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.visibility != 'p':
            if TalkSpeaker.objects\
                .filter(speaker__user=self.user_id, talk__status='accepted')\
                .count()>0:
                raise ValidationError('This profile must be public')

    def setBio(self, body, language=None):
        MultilingualContent.objects.setContent(self, 'bios', language, body)

    def getBio(self, language=None):
        return MultilingualContent.objects.getContent(self, 'bios', language)

post_save.connect(postSaveResizeImageHandler, sender=AttendeeProfile)

class Presence(models.Model):
    """
    Presence of a participant in a conference.
    """
    profile = models.ForeignKey(AttendeeProfile, related_name='presences')
    conference = models.CharField(max_length=10)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('profile', 'conference'),)

class AttendeeLinkManager(models.Manager):
    def findLinks(self, uid):
        return AttendeeLink.objects.filter(
                models.Q(attendee1=uid) |
                models.Q(attendee2=uid))

    def getLink(self, uid1, uid2):
        return AttendeeLink.objects.get(
                models.Q(attendee1=uid1, attendee2=uid2) |
                models.Q(attendee1=uid2, attendee2=uid1))

class AttendeeLink(models.Model):
    """
    Connection between two participants
    """
    attendee1 = models.ForeignKey(AttendeeProfile, related_name='link1')
    attendee2 = models.ForeignKey(AttendeeProfile, related_name='link2')
    message = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    objects = AttendeeLinkManager()

class SpeakerManager(models.Manager):
    def byConference(self, conf, only_accepted=True, talk_type=None):
        """
        Return the speakers from a conference
        """
        qs = TalkSpeaker.objects\
            .filter(talk__conference=conf)\
            .values('speaker')
        if only_accepted:
            qs = qs.filter(talk__status='accepted')
        if talk_type:
            if isinstance(talk_type, (list, tuple)):
                qs = qs.filter(talk__type__in=talk_type)
            else:
                qs = qs.filter(talk__type=talk_type)
        return Speaker.objects.filter(user__in=qs)


class Speaker(models.Model, UrlMixin):
    user = models.OneToOneField('auth.User', primary_key=True)

    objects = SpeakerManager()

    def __unicode__(self):
        return '%s %s' % (self.user.first_name, self.user.last_name)

    def talks(self, conference=None, include_secondary=True, status=None):
        """
        Build a QueryBuilder, try to fetch all the talks for the current speaker,
        in function of the status and the selected conference.
        """
        qs = TalkSpeaker.objects.filter(speaker=self)
        if status in TALK_STATUS._db_values:
            qs = qs.filter(talk__status=status)
        elif status is not None:
            raise ValueError('status unknown')
        if not include_secondary:
            qs = qs.filter(helper=False)
        if conference is not None:
            qs = qs.filter(talk__conference=conference)
        return Talk.objects.filter(id__in=qs.values('talk'))


TALK_LANGUAGES = dsettings.LANGUAGES

TALK_STATUS = Choices(
    ('proposed', _('Proposed')),
    ('accepted', _('Accepted')),
    ('canceled', _('Canceled')),
    ('waitlist', _('Waitlist')),
)

VIDEO_TYPE = (
    ('viddler_oembed', 'oEmbed (Youtube, Vimeo, ...)'),
    ('download', 'Download'),
)

TALK_LEVEL = Choices(
    ('beginner',     _('Beginner')),
    ('intermediate', _('Intermediate')),
    ('advanced',     _('Advanced')),
)


class TalkManager(models.Manager):

    def get_queryset(self):
        return self._QuerySet(self.model)

    def __getattr__(self, name):
        return getattr(self.all(), name)

    class _QuerySet(QuerySet):

        def _filter_by_status(self, status, conference=None):
            assert status in TALK_STATUS._db_values
            qs = self.filter(status=status)
            if conference:
                qs = qs.filter(conference=conference)
            return qs

        def proposed(self, conference=None):
            return self._filter_by_status(TALK_STATUS.proposed, conference=conference)

        def accepted(self, conference=None):
            return self._filter_by_status(TALK_STATUS.accepted, conference=conference)

        def canceled(self, conference=None):
            return self._filter_by_status(TALK_STATUS.canceled, conference=conference)

        def waitlist(self, conference=None):
            return self._filter_by_status(TALK_STATUS.waitlist, conference=conference)

    def createFromTitle(self, title, sub_title, conference, speaker,
                        prerequisites, abstract_short, abstract_extra,
                        status=TALK_STATUS.proposed, language='en',
                        level=TALK_LEVEL.beginner,
                        domain_level=TALK_LEVEL.beginner,
                        domain='',
                        training_available=False,
                        type='t_30'):
        slug = slugify(title)
        talk = Talk()
        talk.title = title
        talk.domain = domain
        talk.domain_level = domain_level
        talk.sub_title = sub_title
        talk.prerequisites = prerequisites
        talk.abstract_short = abstract_short
        talk.conference = conference
        talk.status = status
        talk.language = language
        talk.level = level
        talk.abstract_extra = abstract_extra
        talk.training_available = training_available
        talk.type = type
        with transaction.atomic():
            count = 0
            check = slug
            while True:
                if self.filter(slug=check).count() == 0:
                    break
                count += 1
                check = '%s-%d' % (slug, count)
            talk.slug = check
            talk.save()
            # FIXME: This part should be done in one transaction.
            TalkSpeaker(talk=talk, speaker=speaker).save()
        return talk

# Previous definition of TALK_TYPE, kept around, since some of the
# code in the system uses the codes to checks.
#
# TALK_TYPE = (
#     ('t', 'Talk'),
#     ('i', 'Interactive'),
#     ('r', 'Training'),
#     ('p', 'Poster session'),
#     ('n', 'Panel'),
#     ('h', 'Help desk'),
# )

# Talk types combined with duration. Note that the system uses the
# first character to identify the generic talk type, so these should
# not be changed from the ones listed above.
TALK_TYPE = (
    ('t_30', 'Talk (30 mins)'),
    ('t_45', 'Talk (45 mins)'),
    ('t_60', 'Talk (60 mins)'),
    ('i_60', 'Interactive (60 mins)'),
    ('r_180', 'Training (180 mins)'),
    ('p_180', 'Poster session (180 mins)'),
    ('n_60', 'Panel (60 mins)'),
    ('n_90', 'Panel (90 mins)'),
    ('h_180', 'Help desk (180 mins)'),
)

# Mapping of TALK_TYPE to duration in minutes
TALK_DURATION = {
    't_30': 30,
    't_45': 45,
    't_60': 60,
    'i_60': 60,
    'r_180': 180,
    'p_180': 180,
    'n_60': 60,
    'n_90': 90,
    'h_180': 180,
}

# Admin talk entries
#
# These are usually not eligible for speaker coupons. See the
# create_speaker_coupons.py script for details.
#
TALK_ADMIN_TYPE = (
    ('o', 'Opening session'),
    ('c', 'Closing session'),
    ('l', 'Lightning talk'),
    ('k', 'Keynote'),
    ('r', 'Recruiting session'),
    ('m', 'EPS session'),
    ('p', 'Community session'),
    ('s', 'Open space'),
    ('e', 'Social event'),
    ('x', 'Reserved slot'),
    ('z', 'Sponsored session'),
)


class Talk(models.Model, UrlMixin):
    title = models.CharField(_('Talk title'), max_length=80)
    sub_title = models.CharField(_('Sub title'), max_length=1000, default="", blank=True)
    slug = models.SlugField(max_length=100, unique=True)
    prerequisites = models.CharField(_('prerequisites'), help_text="What should attendees know already",default="", blank=True, max_length=150)
    conference = models.CharField(help_text='name of the conference', max_length=20)
    admin_type = models.CharField(max_length=1, choices=TALK_ADMIN_TYPE, blank=True)
    speakers = models.ManyToManyField(Speaker, through='TalkSpeaker')
    language = models.CharField(_('Language'), max_length=3, choices=TALK_LANGUAGES, default="en")
    abstracts = GenericRelation(
        MultilingualContent,
        verbose_name=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'))
    abstract_short = models.TextField(
        verbose_name=_('Talk abstract short'),
        help_text=_('<p>Please enter a short description of the talk you are submitting.</p>'), default="")

    abstract_extra = models.TextField(
        verbose_name=_('Talk abstract extra'),
        help_text=_('<p>Please enter instructions for attendees.</p>'),
        blank=True,
        default="")

    slides = models.FileField(upload_to=_fs_upload_to('slides'), blank=True)
    video_type = models.CharField(max_length=30, choices=VIDEO_TYPE,
                                  blank=True)
    video_url = models.TextField(blank=True)
    video_file = models.FileField(upload_to=_fs_upload_to('videos'),
                                  blank=True)
    teaser_video = models.URLField(
        _('Teaser video'),
        blank=True,
        help_text=_('Insert the url for your teaser video'))
    status = models.CharField(max_length=8, choices=TALK_STATUS)

    # TODO: should be renamed to python_level,
    # because we added also domain_level
    level = models.CharField(
        _('Audience Python level'),
        default='beginner',
        max_length=12,
        choices=TALK_LEVEL)

    training_available = models.BooleanField(default=False)
    type = models.CharField(max_length=5, choices=TALK_TYPE, default='t_30')

    domain = models.CharField(
        max_length=20,
        choices=dsettings.CONFERENCE_TALK_DOMAIN,
        default=dsettings.CONFERENCE_TALK_DOMAIN.other,
        blank=True
    )
    domain_level = models.CharField(
        _("Audience Domain Level"),
        default=TALK_LEVEL.beginner,
        max_length=12,
        choices=TALK_LEVEL  # using the same Choices as regular talk level
    )

    duration = models.IntegerField(
        _('Duration'),
        default=0,
        help_text=_('This is the duration of the talk. '
                    'Set to 0 to use the default talk duration.'))

    # Suggested Tags, normally, should use a submission model.
    suggested_tags = models.CharField(max_length=100, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    tags = TaggableManager(through=ConferenceTaggedItem)
    objects = TalkManager()

    class Meta:
        ordering = ['title']

    def save(self, *args, **kwargs):
        # The duration is taken directly from talk's type, unless it was
        # customized
        if (self.duration == 0 or
            self.duration in TALK_DURATION.values()):
            # duration was previously set to a standard value, so update
            # the value to the talk length
            self.duration = TALK_DURATION[self.type]
        else:
            # Custom curation: leave as it is; this is useful for e.g.
            # workshops
            pass
        super(Talk, self).save(*args, **kwargs)

    def __unicode__(self):
        return '%s [%s][%s][%s]' % (self.title, self.conference, self.language, self.duration)

    def get_absolute_url(self):
        return reverse('conference-talk', args=[self.slug])

    def get_admin_url(self):
        return reverse('admin:conference_talk_change', args=[self.id])

    get_url_path = get_absolute_url

    def get_event(self):
        try:
            return self.event_set.all()[0]
        except IndexError:
            return None

    def get_event_list(self):
        try:
            return self.event_set.all()
        except IndexError:
            return None

    def get_all_speakers(self):
        return self.speakers.all()

    def setAbstract(self, body, language=None):
        MultilingualContent.objects.setContent(self, 'abstracts', language, body)

    def getAbstract(self, language=None):
        return MultilingualContent.objects.getContent(self, 'abstracts', language)

class TalkSpeaker(models.Model):
    talk = models.ForeignKey(Talk)
    speaker = models.ForeignKey(Speaker)
    helper = models.BooleanField(default=False)

    class Meta:
        unique_together = (('talk', 'speaker'),)

class FareManager(models.Manager):
    def get_queryset(self):
        return self._QuerySet(self.model)

    def __getattr__(self, name):
        return getattr(self.all(), name)

    class _QuerySet(QuerySet):
        def available(self, conference=None):
            today = datetime.date.today()
            q1 = models.Q(start_validity=None, end_validity=None)
            q2 = models.Q(start_validity__lte=today, end_validity__gte=today)
            qs = self.filter(q1 | q2)
            if conference:
                qs = qs.filter(conference=conference)
            return qs

# TODO(artcz) Convert those to Choices for easier enum-like interface

FARE_TICKET_TYPES = Choices(
    ('conference', 'Conference ticket'),
    ('partner', 'Partner Program'),
    ('event', 'Event'),
    ('other', 'Other'),
)

FARE_PAYMENT_TYPE = (
    ('p', 'Payment'),
    ('v', 'Voucher'),
    ('d', 'Deposit'),
)

FARE_TYPES = (
    ('c', 'Company'),
    ('s', 'Student'),
    ('p', 'Personal'),
)
class Fare(models.Model):
    conference = models.CharField(help_text='Conference code', max_length=20)
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    start_validity = models.DateField(null=True, blank=True)
    end_validity = models.DateField(null=True, blank=True)
    recipient_type = models.CharField(max_length=1, choices=FARE_TYPES, default='p')
    ticket_type = models.CharField(max_length=10, choices=FARE_TICKET_TYPES, default='conference', db_index=True)
    payment_type = models.CharField(max_length=1, choices=FARE_PAYMENT_TYPE, default='p')
    blob = models.TextField(blank=True)

    objects = FareManager()

    def __unicode__(self):
        return '%s - %s' % (self.code, self.conference)

    class Meta:
        unique_together = (('conference', 'code'),)

    def valid(self):
        #numb = len(list(Ticket.objects.all()))
        today = datetime.date.today()
        try:
            validity = self.start_validity <= today <= self.end_validity
        except TypeError:
            # if we have TypeError that probably means either start or end (or
            # both) are set to None. That by default means fare is invalid
            # right now.
            validity = False
        #validity = numb < settings.MAX_TICKETS
        return validity

    def fare_type(self):

        """ Return the fare type based on the .recipient_type
        """
        return dict(FARE_TYPES).get(self.recipient_type, 'Regular')

    def calculated_price(self, qty=1, **kw):
        from conference.listeners import fare_price
        params = dict(kw)
        params['qty'] = qty
        calc = {
            'total': self.price * qty,
            'params': params,
        }
        fare_price.send(sender=self, calc=calc)
        return calc['total']

    def create_tickets(self, user):

        """ Creates and returns the tickets associated with this rate.

            Normally each fare involves just one ticket, but this
            behavior can be modified by a listener attached to the
            signal fare_tickets.

            The instances returned by this method have an additional
            attribute `fare_description` (volatile) and contains a
            description of the fare specific for the single ticket.

        """
        from conference.listeners import fare_tickets
        params = {
            'user': user,
            'tickets': []
        }
        fare_tickets.send(sender=self, params=params)
        if not params['tickets']:
            t = Ticket(user=user, fare=self)
            t.fare_description = self.name
            t.save()
            params['tickets'].append(t)
        return params['tickets']

class TicketManager(models.Manager):
    def get_queryset(self):
        return self._QuerySet(self.model)

    def __getattr__(self, name):
        return getattr(self.all(), name)

    class _QuerySet(QuerySet):
        def conference(self, conference):
            return self.filter(fare__conference=conference)

TICKET_TYPE = (
    ('standard', 'standard'),
    ('staff', 'staff'),
)

class Ticket(models.Model):
    user = models.ForeignKey(
        'auth.User',
        help_text=_('Buyer of the ticket'))
    name = models.CharField(
        max_length=60,
        blank=True,
        help_text=_('Attendee name, i.e. the person who will attend the conference.'))
    fare = models.ForeignKey(Fare)
    frozen = models.BooleanField(
        default=False,
        verbose_name=_('ticket canceled / invalid / frozen'),
        help_text=_('If a ticket was canceled or otherwise needs to be marked as '
                    'invalid, please check this checkbox to indicate this.'),
        )
    ticket_type = models.CharField(max_length=8, choices=TICKET_TYPE, default='standard')

    objects = TicketManager()

    def __unicode__(self):
        return 'Ticket "%s" (%s)' % (self.fare.name, self.fare.code)

class Sponsor(models.Model):
    """
    Through the list of SponsorIncome instance of Sponsor it is connected
    with information about all made sponsorships.
    Always SponsorIncome the conference is shown, as in other places,
    with an alphanumeric key is not connected to any table.
    """
    sponsor = models.CharField(max_length=100, help_text='Name of the sponsor')
    slug = models.SlugField()
    url = models.URLField(blank=True)
    logo = models.ImageField(
        upload_to=_fs_upload_to('sponsor'), blank=True,
        help_text='Insert a raster image big enough to be scaled as needed'
    )
    alt_text = models.CharField(max_length=150, blank=True)
    title_text = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ['sponsor']

    def __unicode__(self):
        return self.sponsor

post_save.connect(postSaveResizeImageHandler, sender=Sponsor)

class SponsorIncome(models.Model):
    sponsor = models.ForeignKey(Sponsor)
    conference = models.CharField(max_length=20)
    income = models.PositiveIntegerField()
    tags = TagField()

    class Meta:
        ordering = ['conference']

class MediaPartner(models.Model):
    """
    The media partners are the sponsors who do not pay but that offer visibility
    of some kind.
    """
    partner = models.CharField(max_length=100, help_text='The media partner name')
    slug = models.SlugField()
    url = models.URLField(blank=True)
    logo = models.ImageField(
        upload_to=_fs_upload_to('media-partner'), blank = True,
        help_text='Insert a raster image big enough to be scaled as needed'
    )

    class Meta:
        ordering = ['partner']

    def __unicode__(self):
        return self.partner

post_save.connect(postSaveResizeImageHandler, sender=MediaPartner)

class MediaPartnerConference(models.Model):
    partner = models.ForeignKey(MediaPartner)
    conference = models.CharField(max_length = 20)
    tags = TagField()

    class Meta:
        ordering = ['conference']

class ScheduleManager(models.Manager):
    def attendees(self, conference, forecast=False):
        """
        Returns the number of participants for each of the conference schedule.
        """
        return settings.SCHEDULE_ATTENDEES(conference, forecast)

    def events_score_by_attendance(self, conference):
        """
        Using events Interest returns a "Presence score" for each event;
        The score is proportional to the number of people who have expressed
        interest in that event.
        """
        # I consider it an expression of interest, interest > 0, as the will to
        # participate in an event and add the user among the participants. If the user
        # has voted the most contemporary events. I consider his presence in proportion
        # (so events can have fractional score)
        events = defaultdict(set)
        for x in EventInterest.objects\
                    .filter(event__schedule__conference=conference, interest__gt=0)\
                    .select_related('event__schedule'):
            events[x.event].add(x.user_id)
        # In addition to EventInterest keep account of EventBooking,
        # the confidence in these cases in even greater.
        for x in EventBooking.objects\
                    .filter(event__schedule__conference=conference)\
                    .select_related('event__schedule'):
            events[x.event].add(x.user_id)

        # Associate to each event the number of votes it has obtained;
        # the operation is complicated by the fact that not all votes have the
        # same weight; if a user has marked as +1 two events to occur
        # Parallel obviously can not participate in both, so the
        # his vote should be scaled
        scores = defaultdict(lambda: 0.0)
        for evt, users in events.items():
            group = list(Event.objects.group_events_by_times(events, event=evt))[0]
            while users:
                u = users.pop()
                # what is the presence of `` evt` u` for the event? If `u` does not take
                # part in no other event of the same group, then 1, otherwise a value proportional
                # to the number of events of interest.
                found = [ evt ]
                for other in group:
                    if other != evt:
                        try:
                            events[other].remove(u)
                        except KeyError:
                            pass
                        else:
                            found.append(other)
                score = 1.0 / len(found)
                for f in found:
                    scores[f.id] += score
        return scores

    def expected_attendance(self, conference, factor=0.85):
        """
        Return for each event prediction of participation based on EventInterest
        """
        seats_available = defaultdict(lambda: 0)
        for row in EventTrack.objects\
                    .filter(event__schedule__conference=conference)\
                    .values('event', 'track__seats'):
            seats_available[row['event']] += row['track__seats']

        scores = self.events_score_by_attendance(conference)
        events = Event.objects\
            .filter(schedule__conference=conference)\
            .select_related('schedule')

        output = {}
        # Now I have to make the forecast of the participants for each event,
        # to make it divide the score of an event by the number of voters who
        # have expressed a vote for an event in the same time band * *; the number
        # I get is a k factor when multiplied by the forecast of people a day gives
        # me an indication of how many people are expected for the event.
        forecasts = self.attendees(conference, forecast=True)

        # to calculate the score for a time band I have to do a double for the
        # events, to limit the number of internal iterations I group events per day
        event_by_day = defaultdict(set)
        for e in events:
            event_by_day[e.schedule_id].add(e)

        for event in events:
            score = scores[event.id]
            group = list(Event.objects\
                .group_events_by_times(event_by_day[event.schedule_id], event=event))[0]

            group_score = sum([ scores[e.id] for e in group ])
            if group_score:
                k = score / group_score
            else:
                k = 0
            expected = k * forecasts[event.schedule_id] * factor
            seats = seats_available.get(event.id, 0)
            output[event.id] = {
                'score': score,
                'seats': seats,
                'expected': expected,
                'overbook': seats and expected > seats,
            }

        return output

class Schedule(models.Model):
    """
    Directly into the schedule we have an indication of the conference,
    a free alphanumeric field, and the day to which it relates.
    Though ForeignKey the schedule is attached to and track events.
    The latter can be the talk of the events or "custom" as the pyBirra,
    and are connected to the track in the "weak" mode, through a tagfield.
    """
    conference = models.CharField(help_text = 'nome della conferenza', max_length = 20)
    slug = models.SlugField()
    date = models.DateField()
    description = models.TextField(blank=True)

    objects = ScheduleManager()

    class Meta:
        ordering = ['date']

    def __unicode__(self):
        return '{0}: {1}'.format(self.conference, self.date)

    def speakers(self):
        qs = Event.objects\
            .filter(schedule=self, talk__id__isnull=False)\
            .values('talk__talkspeaker__speaker')
        return Speaker.objects.filter(user__in=qs)


class Track(models.Model):
    schedule = models.ForeignKey(Schedule)
    track = models.CharField('nome track', max_length=20)
    title = models.TextField('titolo della track', help_text='HTML supportato')
    seats = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField('ordine', default=0)
    translate = models.BooleanField(default=False)
    outdoor = models.BooleanField(default=False)

    def __unicode__(self):
        return self.track

class EventManager(models.Manager):
    def group_events_by_times(self, events, event=None):
        """
        Groups the events, obviously belonging to different track, which they overlap in time.
        Return a generator that at each iteration returns a group (list) of events.
        """
        def overlap(range1, range2):
            # http://stackoverflow.com/questions/9044084/efficient-data-range-overlap-calculation-in-python
            latest_start = max(range1[0], range2[0])
            earliest_end = min(range1[1], range2[1])
            _overlap = (earliest_end - latest_start)
            return _overlap.days == 0 and _overlap.seconds > 0

        def extract_group(event, events):
            group = []
            r0 = event.get_time_range()
            for ix in reversed(range(len(events))):
                r1 = events[ix].get_time_range()
                if r0[0].date() == r1[0].date() and overlap(r0, r1):
                    group.append(events.pop(ix))
            return group

        if event:
            group = extract_group(event, list(events))
            yield group
        else:
            sorted_events = sorted(
                filter(lambda x: x.get_duration() > 0, events),
                key=lambda x: x.get_duration())
            while sorted_events:
                evt0 = sorted_events.pop()
                group = [evt0] + extract_group(evt0, sorted_events)
                yield group

class Event(models.Model):
    schedule = models.ForeignKey(Schedule)
    start_time = models.TimeField()

    talk = models.ForeignKey(Talk, blank=True, null=True)
    custom = models.TextField(
        blank=True,
        help_text="title for a custom event (an event without a talk)")
    abstract = models.TextField(
        blank=True,
        help_text="description for a custom event")

    duration = models.PositiveIntegerField(
        default=0,
        help_text='duration of the event (in minutes). Override the talk duration if present')

    tags = models.CharField(
        max_length=200, blank=True,
        help_text='comma separated list of tags. Something like: special, break, keynote')
    tracks = models.ManyToManyField(Track, through='EventTrack')
    sponsor = models.ForeignKey(Sponsor, blank=True, null=True)
    video = models.CharField(max_length=1000, blank=True)

    bookable = models.BooleanField(default=False)
    seats = models.PositiveIntegerField(
        default=0,
        help_text='seats available. Override the track default if set')

    objects = EventManager()

    class Meta:
        ordering = ['start_time']

    def __unicode__(self):
        if self.talk:
            return '%s - %smin' % (self.talk.title, self.talk.duration)
        else:
            return self.custom

    def get_duration(self):
        if self.duration:
            return self.duration
        elif self.talk:
            return self.talk.duration
        else:
            return 0

    def get_time_range(self):
        n = datetime.datetime.combine(self.schedule.date, self.start_time)
        return (
            n, (n + datetime.timedelta(seconds=self.get_duration() * 60))
        )

    def get_description(self):
        if self.talk:
            return self.talk.title
        else:
            return self.custom

    def get_all_tracks_names(self):
        from tagging.utils import parse_tag_input
        return parse_tag_input(self.track)

    def get_track(self):
        """
        returns to the first track instance with the specified values or None if the event
        It is of special type
        """
        # XXX: Use the tag template get track event that hunts the query
        dbtracks = dict( (t.track, t) for t in self.schedule.track_set.all())
        for t in tagging.models.Tag.objects.get_for_object(self):
            if t.name in dbtracks:
                return dbtracks[t.name]

    def split(self, time):
        """
        It divides the event into multiple events lasting up to `time` minutes.
        """
        if self.talk_id and self.duration == 0:
            original = self.talk.duration
        else:
            original = self.duration
        if time >= original:
            return 0

        myid = self.id
        tracks = self.tracks.all()

        self.duration = time
        original -= time
        self.save()
        count = 1

        while original > 0:
            self.id = None
            dt = datetime.datetime.combine(datetime.date.today(), self.start_time)
            dt += datetime.timedelta(minutes=time)
            self.start_time = dt.time()
            self.save()

            for t in tracks:
                EventTrack.objects.create(track=t, event=self)

            original -= time
            count += 1

        self.id = myid
        return count

class EventTrack(models.Model):
    track = models.ForeignKey(Track)
    event = models.ForeignKey(Event)

    class Meta:
        unique_together = (('track', 'event',),)

class EventInterest(models.Model):
    event = models.ForeignKey(Event)
    user = models.ForeignKey('auth.User')
    interest = models.IntegerField()

    class Meta:
        unique_together = (('user', 'event'),)

class EventBookingManager(models.Manager):
    def booking_status(self, eid):
        seats = Event.objects.values('seats').get(id=eid)['seats']
        if not seats:
            seats = sum(EventTrack.objects\
                .filter(event=eid)\
                .values_list('track__seats', flat=True))
        booked = list(EventBooking.objects\
            .filter(event=eid)\
            .values_list('user', flat=True))
        return {
            'seats': seats,
            'booked': booked,
            'available': seats - len(booked),
        }

    def booking_available(self, eid, uid):
        st = self.booking_status(eid)
        return (uid in st['booked']) or (st['available'] > 0)

    def book_event(self, eid, uid):
        try:
            e = EventBooking.objects.get(event=eid, user=uid)
        except EventBooking.DoesNotExist:
            e = EventBooking(event_id=eid, user_id=uid)
            e.save()
            signals.event_booked.send(sender=Event, booked=True, event_id=eid, user_id=uid)
        return e

    def cancel_reservation(self, eid, uid):
        try:
            e = EventBooking.objects.get(event=eid, user=uid)
        except EventBooking.DoesNotExist:
            return
        e.delete()
        signals.event_booked.send(sender=Event, booked=False, event_id=eid, user_id=uid)

class EventBooking(models.Model):
    event = models.ForeignKey(Event)
    user = models.ForeignKey('auth.User')

    objects = EventBookingManager()

    class Meta:
        unique_together = (('user', 'event'),)

class Hotel(models.Model):
    """
    Hotels allow you to track affiliated places and not where finding accommodations during the conference.
    """
    name = models.CharField('Name', max_length = 100)
    telephone = models.CharField('Phone', max_length = 50, blank = True)
    url = models.URLField(blank = True)
    email = models.EmailField('email', blank = True)
    availability = models.CharField('Availability', max_length = 50, blank = True)
    price = models.CharField('Price', max_length = 50, blank = True)
    note = models.TextField('note', blank = True)
    affiliated = models.BooleanField('Affiliated', default = False)
    visible = models.BooleanField('visibile', default = True)
    address = models.CharField('Address', max_length = 200, default = '', blank = True)
    lng = models.FloatField('longitude', default = 0.0, blank = True)
    lat = models.FloatField('latitude', default = 0.0, blank = True)
    modified = models.DateField(auto_now = True)

    class Meta:
        ordering = [ 'name' ]

    def __unicode__(self):
        return self.name

SPECIAL_PLACE_TYPES = (
    ('conf-hq', 'Conference Site'),
    ('pyevents', 'PyEvents'),
)
class SpecialPlace(models.Model):
    name = models.CharField('Name', max_length = 100)
    address = models.CharField('Address', max_length = 200, default = '', blank = True)
    type = models.CharField(max_length = 10, choices=SPECIAL_PLACE_TYPES)
    url = models.URLField(blank = True)
    email = models.EmailField('Email', blank = True)
    telephone = models.CharField('Phone', max_length = 50, blank = True)
    note = models.TextField('note', blank = True)
    visible = models.BooleanField('visibile', default = True)
    lng = models.FloatField('longitude', default = 0.0, blank = True)
    lat = models.FloatField('latitude', default = 0.0, blank = True)

    class Meta:
        ordering = [ 'name' ]

    def __unicode__(self):
        return self.name

try:
    assert settings.GOOGLE_MAPS['key']
except (KeyError, TypeError, AssertionError):
    pass
else:
    def postSaveHotelHandler(sender, **kwargs):
        query = sender.objects.exclude(address = '').filter(lng = 0.0).filter(lat = 0.0)
        for obj in query:
            data = conference.gmap.geocode(
                obj.address,
                settings.GOOGLE_MAPS['key'],
                settings.GOOGLE_MAPS.get('country')
            )
            if data['Status']['code'] == 200:
                point = data['Placemark'][0]['Point']['coordinates']
                lng, lat = point[0:2]
                obj.lng = lng
                obj.lat = lat
                obj.save()
    post_save.connect(postSaveHotelHandler, sender=Hotel)
    post_save.connect(postSaveHotelHandler, sender=SpecialPlace)

class DidYouKnow(models.Model):
    """
    Do you know that ?
    """
    visible = models.BooleanField('visible', default = True)
    messages = GenericRelation(MultilingualContent)

class Quote(models.Model):
    who = models.CharField(max_length=100)
    conference = models.CharField(max_length=20)
    text = models.TextField()
    activity = models.CharField(max_length=50, blank=True)
    image = models.ImageField(upload_to=_fs_upload_to('quote', 'who'), blank=True)

    class Meta:
        ordering = ['conference', 'who']

class VotoTalk(models.Model):
    user = models.ForeignKey('auth.User')
    talk = models.ForeignKey(Talk)
    vote = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = (('user', 'talk'),)
        verbose_name = 'Talk voting'
        verbose_name_plural = 'Talk votings'
#
#def _clear_track_cache(sender, **kwargs):
#    if hasattr(sender, 'schedule_id'):
#        Track.objects.clear_cache(sender.schedule_id)
#post_save.connect(_clear_track_cache, sender=Track)
#
#def _clear_talkspeaker_cache(sender, **kwargs):
#    o = kwargs['instance']
#    if isinstance(o, Talk):
#        conference = o.conference
#    else:
#        conference = None
#    TalkSpeaker.objects.clear_cache(conference)
#post_save.connect(_clear_talkspeaker_cache, sender=Talk)
#post_save.connect(_clear_talkspeaker_cache, sender=Speaker)
#
#def _clear_schedule_cache(sender, **kwargs):
#    o = kwargs['instance']
#    if isinstance(o, Event):
#        conference = o.schedule.conference
#    else:
#        conference = o.event.schedule.conference
#    Schedule.objects.clear_cache(conference)
#post_save.connect(_clear_schedule_cache, sender=Event)
#post_save.connect(_clear_schedule_cache, sender=EventInterest)

from conference import listeners


# ========================================
# ExchangeRates
# TODO: split conference/models.py to multiple files and put it this model in a
# separate file.
# ========================================
class ExchangeRate(models.Model):
    """
    Store Exchange Rate relative to Euro
    """
    datestamp = models.DateField()
    currency = models.CharField(max_length=3)  # iso 4217 currency code
    # rate == how much curency for 1 EUR.
    rate = models.DecimalField(max_digits=10, decimal_places=5)

    def __str__(self):
        return "%s %s" % (self.currency, self.datestamp)


# ========================================
# CaptchaQuestions
# TODO: split conference/models.py to multiple files and put it this model in a
# separate file.
# ========================================

class CaptchaQuestionManager(models.Manager):

    def get_random_question(self):
        qs = self.get_queryset().filter(enabled=True)
        try:
            return qs.order_by("?")[0]
        except IndexError:
            raise CaptchaQuestion.NoQuestionsAvailable()


class CaptchaQuestion(TimeStampedModel):

    class NoQuestionsAvailable(Exception):
        pass

    question = models.CharField(max_length=255)
    answer   = models.CharField(max_length=255)
    enabled  = models.BooleanField(default=True)

    objects = CaptchaQuestionManager()

    def __str__(self):
        return self.question
