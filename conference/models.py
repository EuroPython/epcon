import datetime
import os
import os.path
import uuid
import pytz
from collections import defaultdict
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import exceptions
from django.core.cache import cache
from django.urls import reverse
from django.db import models, transaction
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import (
    GenericForeignKey,
    GenericRelation
)
from django_extensions.db.fields.json import JSONField

import shortuuid
from model_utils import Choices
from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager
from taggit.models import GenericTaggedItemBase, ItemBase, TagBase


CURRENT_CONFERENCE_CACHE_KEY = 'CONFERENCE_CURRENT'


# ConferenceTag and ConferenceTaggedItem are used to create a "namesapce"
# for the related tags to a conference.
class ConferenceTagQuerySet(models.QuerySet):
    def annotate_with_usage(self):
        return self.annotate(
            usage=models.Count('conference_conferencetaggeditem_items')
        )

    def order_by_usage(self, asc=False):
        key = 'usage' if asc else '-usage'
        return self.annotate_with_usage().order_by(key)


class ConferenceTag(TagBase):
    objects = ConferenceTagQuerySet.as_manager()
    category = models.CharField(max_length=50, default='', blank=True)

    class Meta:
        ordering = ['name']

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
    tag = models.ForeignKey(
        ConferenceTag,
        related_name="%(app_label)s_%(class)s_items",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("Tagged Item")
        verbose_name_plural = _("Tagged Items")


class ConferenceManager(models.Manager):
    def current(self):
        data = cache.get(CURRENT_CONFERENCE_CACHE_KEY)
        a_week = 60 * 60 * 24 * 7

        if data is None:
            data = self.get(code=settings.CONFERENCE_CONFERENCE)
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

    def __str__(self):
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
            while d <= self.conference_end:
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
        today = timezone.now().date()
        try:
            return self.cfp_start <= today <= self.cfp_end
        except TypeError:
            # there is no date, return False
            return False

    def voting(self):
        today = timezone.now().date()
        try:
            return self.voting_start <= today <= self.voting_end
        except TypeError:
            # there is no date, return False
            return False

    def conference(self):
        today = timezone.now().date()
        return self.conference_start <= today <= self.conference_end

    @property
    def has_finished(self):
        today = timezone.now().date()
        return today > self.conference_end


class MultilingualContentManager(models.Manager):
    def setContent(self, object, content, language, body):
        if language is None:
            language = settings.LANGUAGE_CODE.split('-', 1)[0]
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
            language = settings.LANGUAGE_CODE.split('-', 1)[0]
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
                return records.get(settings.LANGUAGE_CODE, list(records.values())[0])


class MultilingualContent(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
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

        ipath = os.path.join(settings.MEDIA_ROOT, fpath)

        if os.path.exists(ipath):
            os.unlink(ipath)

        return fpath


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
            if last is None or counter > last:
                last = counter

        if last is not None:
            slug = '%s-%d' % (slug, last + 1)
        elif not slug:
            # if there is no slug, because the firstname or the lastname are empties,
            # we will return '-1'
            slug = '-1'
        return slug

    def randomUUID(self, length=6):
        import string
        import random
        return ''.join(random.sample(string.ascii_letters + string.digits, length))

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


ATTENDEEPROFILE_VISIBILITY = Choices(
    ("p", "PUBLIC", "Publicly available"),
    ("m", "PARTICIPANTS_ONLY", "Visible to EuroPython attendees"),
    ("x", "PRIVATE", "Visible only to you"),
)

ATTENDEEPROFILE_GENDER = Choices(
    ("m", "MALE", "Male"),
    ("f", "FEMALE", "Female"),
    ("o", "OTHER", "Other"),
    ("x", "PREFER_NOT_TO_SAY", "Prefer not to say"),
)


class AttendeeProfile(models.Model):
    """
    It's the profile of a participant (including the speaker) at the conference, there is a connection
    to the auth.User via a ForeignKey.
    """
    user = models.OneToOneField(get_user_model(), primary_key=True, on_delete=models.CASCADE)
    slug = models.SlugField(unique=True)
    uuid = models.CharField(max_length=6, unique=True)

    image = models.ImageField(upload_to=_fs_upload_to('profile'), blank=True)

    # NOTE(artcz): This is currently deprecated field, replaced with is_minor
    # because that's what we basically used it for.
    birthday = models.DateField(_('Birthday'), null=True, blank=True)

    # minor == <18 years old.
    is_minor = models.BooleanField(default=False)

    phone = models.CharField(
        _('Phone'),
        max_length=30, blank=True,
        help_text=_(
            "We require a mobile phone number for all speakers "
            "for last minute contacts and in case we need "
            "timely clarification (if no reponse to previous emails). "
            "Use the international format (e.g.: +44 123456789)."
        ),
    )

    gender = models.CharField(
        max_length=1, choices=ATTENDEEPROFILE_GENDER,
        help_text=_(
            "We use this information for statistics related to conference "
            "attendance diversity."
        )
    )

    personal_homepage = models.URLField(_('Personal homepage'), blank=True)
    company = models.CharField(_('Company'), max_length=50, blank=True)
    company_homepage = models.URLField(_('Company homepage'), blank=True)
    job_title = models.CharField(_('Job title'), max_length=50, blank=True)

    location = models.CharField(_('Location'), max_length=100, blank=True)
    bios = GenericRelation(MultilingualContent)

    visibility = models.CharField(max_length=1, choices=ATTENDEEPROFILE_VISIBILITY, default='x')

    objects = AttendeeProfileManager()

    def __str__(self):
        return self.slug

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.visibility != 'p':
            if TalkSpeaker.objects.filter(speaker__user=self.user_id, talk__status='accepted').exists():
                raise ValidationError('This profile must be public')

    def setBio(self, body, language=None):
        MultilingualContent.objects.setContent(self, 'bios', language, body)

    def getBio(self, language=None):
        return MultilingualContent.objects.getContent(self, 'bios', language)


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


class Speaker(models.Model):
    user = models.OneToOneField(get_user_model(), primary_key=True, on_delete=models.CASCADE)

    objects = SpeakerManager()

    def __str__(self):
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


TALK_LANGUAGES = settings.LANGUAGES

TALK_STATUS = Choices(
    ('proposed', _('Proposed')),
    ('accepted', _('Accepted')),
    ('canceled', _('Canceled')),
    ('waitlist', _('Waitlist')),
    ('declined', _('Declined')),
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


class TalkQuerySet(models.QuerySet):
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
TALK_TYPE = [
    ('t_30', 'Talk (30 mins)'),
    ('t_45', 'Talk (45 mins)'),
    ('t_60', 'Talk (60 mins)'),
    ('i_60', 'Interactive (60 mins)'),
    ('r_180', 'Training (180 mins)'),
    ('p_45', 'Poster session (45 mins)'),
    ('p_180', 'Poster session (180 mins)'),
    ('n_60', 'Panel (60 mins)'),
    ('n_90', 'Panel (90 mins)'),
    ('h_180', 'Help desk (180 mins)'),
]

TALK_TYPE_CHOICES = Choices(*TALK_TYPE)

# Copy of TALK_TYPE, which defines the types that can be chosen in the
# CFP. The other types remain available via the Django admin.
CFP_TALK_TYPE = [
    ('t_30', 'Talk (30 mins)'),
    ('t_45', 'Talk (45 mins)'),
    #('t_60', 'Talk (60 mins)'),
    ('i_60', 'Interactive (60 mins)'),
    ('r_180', 'Training (180 mins)'),
    ('p_45', 'Poster session (45 mins)'),
    #('p_180', 'Poster session (180 mins)'),
    ('n_60', 'Panel (60 mins)'),
    #('n_90', 'Panel (90 mins)'),
    ('h_180', 'Help desk (180 mins)'),
]



# Mapping of TALK_TYPE to duration in minutes
TALK_DURATION = {
    't_30': 30,
    't_45': 45,
    't_60': 60,
    'i_60': 60,
    'r_180': 180,
    'p_45': 45,
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


def random_shortuuid():
    return shortuuid.ShortUUID().random(length=7)


class Talk(models.Model):
    # CharField because sqlite
    uuid = models.CharField(
        # FIXME(artcz)
        # unique-False because we have al ot of old talks without uuid
        # will update this later once we add some uuids on production
        unique=False,
        max_length=40,
        default=random_shortuuid,
        editable=False,
    )
    created_by = models.ForeignKey(get_user_model(), blank=True, null=True, on_delete=models.deletion.PROTECT)

    title = models.CharField("Talk title", max_length=80)
    sub_title = models.CharField(
        "Sub title", max_length=1000, default="", blank=True
    )
    slug = models.SlugField(max_length=100, unique=True)
    prerequisites = models.CharField(
        "Prerequisites",
        help_text="What should attendees know already",
        default="",
        blank=True,
        max_length=150,
    )
    conference = models.CharField(
        help_text="name of the conference", max_length=20
    )
    admin_type = models.CharField(
        max_length=1, choices=TALK_ADMIN_TYPE, blank=True
    )
    speakers = models.ManyToManyField(Speaker, through="TalkSpeaker")
    language = models.CharField(
        "Language", max_length=3, choices=TALK_LANGUAGES, default="en"
    )
    abstracts = GenericRelation(
        MultilingualContent,
        verbose_name=_("Talk abstract"),
        help_text=_(
            "Please enter a short description of the talk you are submitting. "
            "Be sure to includes the goals of your talk and any prerequisite "
            "required to fully understand it.\n"
            "Suggested size: two or three paragraphs."
        ),
    )
    abstract_short = models.TextField(
        verbose_name="Talk abstract short",
        help_text=(
            "Please enter a short description of the talk you are submitting."
        ),
        default="",
    )

    abstract_extra = models.TextField(
        verbose_name=_("Talk abstract extra"),
        help_text=_("<p>Please enter instructions for attendees.</p>"),
        blank=True,
        default="",
    )

    availability = models.TextField(
        verbose_name=_('Timezone availability'),
        help_text=_('<p>Please enter your time availability.</p>'),
        blank=True,
        default='',
    )

    slides = models.FileField(upload_to=_fs_upload_to("slides"), blank=True)
    slides_url = models.URLField(blank=True)
    repository_url = models.URLField(blank=True)
    video_type = models.CharField(
        max_length=30, choices=VIDEO_TYPE, blank=True
    )
    video_url = models.TextField(blank=True)
    video_file = models.FileField(
        upload_to=_fs_upload_to("videos"), blank=True
    )
    teaser_video = models.URLField(
        _("Teaser video"),
        blank=True,
        help_text=_("Insert the url for your teaser video"),
    )

    status = models.CharField(
        max_length=8, choices=TALK_STATUS, default=TALK_STATUS.proposed
    )

    # TODO: should be renamed to python_level,
    # because we added also domain_level
    level = models.CharField(
        _("Audience Python level"),
        default="beginner",
        max_length=12,
        choices=TALK_LEVEL,
    )

    training_available = models.BooleanField(default=False)
    type = models.CharField(
        max_length=5, choices=TALK_TYPE_CHOICES, default=TALK_TYPE_CHOICES.t_30
    )

    domain = models.CharField(
        max_length=20,
        choices=settings.CONFERENCE_TALK_DOMAIN,
        default=settings.CONFERENCE_TALK_DOMAIN.other,
        blank=True,
    )
    domain_level = models.CharField(
        _("Audience Domain Level"),
        default=TALK_LEVEL.beginner,
        max_length=12,
        choices=TALK_LEVEL,  # using the same Choices as regular talk level
    )

    duration = models.IntegerField(
        _("Duration"),
        default=0,
        help_text=_(
            "This is the duration of the talk. "
            "Set to 0 to use the default talk duration."
        ),
    )

    # Suggested Tags, normally, should use a submission model.
    suggested_tags = models.CharField(max_length=100, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True, null=True)

    tags = TaggableManager(through=ConferenceTaggedItem)
    objects = TalkQuerySet.as_manager()

    class Meta:
        ordering = ["title"]

    def save(self, *args, **kwargs):
        # Handle duration customizations (if any)
        if self.pk is not None:
            # Use 0 duration if the type changed
            old_object = Talk.objects.get(pk=self.pk)
            if old_object.type != self.type:
                self.duration = 0
        if self.duration == 0:
            # Use the talk type's default value in case the duration was
            # set to 0
            self.duration = TALK_DURATION[self.type]
        super(Talk, self).save(*args, **kwargs)

    def __str__(self):
        return "%s [%s][%s][%s]" % (
            self.title,
            self.conference,
            self.language,
            self.duration,
        )

    def get_absolute_url(self):
        return reverse("talks:talk", args=[self.slug])

    def get_schedule_url(self):
        event = self.get_event()
        if not event:
            return None

        url = event.schedule.get_absolute_url()
        slug = urlencode({'selected': self.slug})
        time = event.get_utc_start_datetime().strftime('%H:%M-UTC')
        return f"{url}?{slug}#{time}"

    def get_slides_url(self):

        """ Return the slides URL (relative to the website)
            or None in case no slides are available.

            For externally hosted slides, the URL refers to an absolute URL
            (anything the speaker entered).

        """
        if self.slides and self.slides.url:
            return self.slides.url or None
        else:
            return self.slides_url or None

    def get_admin_url(self):
        return reverse("admin:conference_talk_change", args=[self.id])

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
        MultilingualContent.objects.setContent(
            self, "abstracts", language, body
        )

    def getAbstract(self, language=None):
        # TODO: this method should always return the contents body
        #   and the get_abstract method should be retired
        return MultilingualContent.objects.getContent(
            self, "abstracts", language
        )

    def get_abstract(self, language=None):
        abstract = MultilingualContent.objects.getContent(
            self, "abstracts", language
        )
        if abstract:
            return abstract.body
        else:
            return self.abstract_short

    def set_availability(self, values, language=None):
        encoded_value = '|'.join(values)
        self.availability = encoded_value

    def get_availability(self):
        return self.availability.split('|')


class TalkSpeaker(models.Model):
    talk = models.ForeignKey(Talk, on_delete=models.CASCADE)
    speaker = models.ForeignKey(Speaker, on_delete=models.CASCADE)
    helper = models.BooleanField(default=False)

    class Meta:
        unique_together = (('talk', 'speaker'),)

    def __str__(self):
        return f'[{self.speaker.user}] for {self.talk.title}'


class FareQuerySet(models.QuerySet):
    def available(self, conference=None):
        today = timezone.now().date()
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

FARE_TYPES = Choices(
    ('c', 'company', 'Company'),
    ('p', 'personal', 'Personal'),
    ('s', 'student', 'Student'),
)


class Fare(models.Model):
    conference = models.CharField(help_text='Conference code', max_length=20)
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    start_validity = models.DateField(null=True, blank=True)
    end_validity = models.DateField(null=True, blank=True)
    recipient_type = models.CharField(
        max_length=1,
        choices=FARE_TYPES,
        default=FARE_TYPES.personal,
    )
    ticket_type = models.CharField(max_length=10, choices=FARE_TICKET_TYPES, default='conference', db_index=True)
    payment_type = models.CharField(max_length=1, choices=FARE_PAYMENT_TYPE, default='p')
    blob = models.TextField(blank=True)

    objects = FareQuerySet.as_manager()

    def __str__(self):
        return '%s - %s' % (self.code, self.conference)

    class Meta:
        unique_together = (('conference', 'code'),)

    def valid(self):
        # numb = len(list(Ticket.objects.all()))
        today = timezone.now().date()
        try:
            validity = self.start_validity <= today <= self.end_validity
        except TypeError:
            # if we have TypeError that probably means either start or end (or
            # both) are set to None. That by default means fare is invalid
            # right now.
            validity = False
        # validity = numb < settings.MAX_TICKETS
        return validity

    def fare_type(self):

        """ Return the fare type based on the .recipient_type
        """
        return dict(FARE_TYPES).get(self.recipient_type, 'Regular')

    def calculated_price(self, qty=1, **kw):
        params = dict(kw)
        params['qty'] = qty
        calc = {
            'total': self.price * qty,
            'params': params,
        }
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

    @property
    def is_conference(self):
        """
        Whether it's a conference ticket and is configurable.
        """
        return self.ticket_type == FARE_TICKET_TYPES.conference


class TicketQuerySet(models.QuerySet):
    def conference(self, conference):
        return self.filter(fare__conference=conference)


TICKET_TYPE = (
    ('standard', 'standard'),
    ('staff', 'staff'),
)


class Ticket(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        help_text=_('Ticket assignee'),
        on_delete=models.CASCADE
    )
    name = models.CharField(
        max_length=60,
        blank=True,
        help_text=_('Attendee name, i.e. the person who will attend the conference.'))
    fare = models.ForeignKey(Fare, on_delete=models.CASCADE)
    frozen = models.BooleanField(
        default=False,
        verbose_name=_('ticket canceled / invalid / frozen'),
        help_text=_(
            'If a ticket was canceled or otherwise needs to be marked as '
            'invalid, please check this checkbox to indicate this.'
        ),
    )
    ticket_type = models.CharField(max_length=8, choices=TICKET_TYPE, default='standard')

    objects = TicketQuerySet.as_manager()

    def __str__(self):
        return 'Ticket "%s" (%s)' % (self.fare.name, self.fare.code)

    @property
    def assigned_email(self):
        if getattr(self, 'p3_conference', None):
            return self.p3_conference.assigned_to

        return ''

    @property
    def buyer(self):
        return self.orderitem.order.user.user

    @property
    def is_conference(self):
        return self.fare.ticket_type == FARE_TICKET_TYPES.conference


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

    def __str__(self):
        return self.sponsor


class SponsorIncome(models.Model):
    sponsor = models.ForeignKey(Sponsor, on_delete=models.CASCADE)
    conference = models.CharField(max_length=20)
    income = models.PositiveIntegerField()
    tags = models.CharField(
        max_length=200, blank=True,
        help_text='comma separated list of tags. Something like: special, break, keynote'
    )

    class Meta:
        ordering = ['conference']


class ScheduleManager(models.Manager):

    def attendees(self, conference, forecast=False):
        """
        Returns the number of participants for each of the conference schedule.
        """
        return settings.CONFERENCE_SCHEDULE_ATTENDEES(conference, forecast)


class Schedule(models.Model):
    """
    Directly into the schedule we have an indication of the conference,
    a free alphanumeric field, and the day to which it relates.
    Though ForeignKey the schedule is attached to and track events.
    The latter can be the talk of the events or "custom" as the pyBirra,
    and are connected to the track in the "weak" mode, through a tagfield.
    """
    conference = models.CharField(help_text = 'Name of the conference', max_length = 20)
    slug = models.SlugField()
    date = models.DateField()
    description = models.TextField(blank=True)

    objects = ScheduleManager()

    class Meta:
        ordering = ['date']

    def __str__(self):
        return '{0}: {1}'.format(self.conference, self.date)

    def get_absolute_url(self):
        return reverse('schedule:schedule', kwargs={
            'day': self.date.day,
            'month': self.date.strftime('%B').lower()
        })

    def speakers(self):
        qs = Event.objects.filter(schedule=self, talk__id__isnull=False).values('talk__talkspeaker__speaker')
        return Speaker.objects.filter(user__in=qs)


class Track(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    # XXX This should really be called "name", not "track"
    track = models.CharField('Track name', max_length=20) # Internal track name
    title = models.TextField('Track title', help_text='HTML supported') # Display name
    seats = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    translate = models.BooleanField(default=False)
    outdoor = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def __repr__(self):
        return 'Track(track=%r, title=%r)' % (self.track, self.title)


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
            for ix in reversed(list(range(len(events)))):
                r1 = events[ix].get_time_range()
                if r0[0].date() == r1[0].date() and overlap(r0, r1):
                    group.append(events.pop(ix))
            return group

        if event:
            group = extract_group(event, list(events))
            yield group
        else:
            sorted_events = sorted(
                [x for x in events if x.get_duration() > 0],
                key=lambda x: x.get_duration())
            while sorted_events:
                evt0 = sorted_events.pop()
                group = [evt0] + extract_group(evt0, sorted_events)
                yield group


class Event(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    start_time = models.TimeField()

    talk = models.ForeignKey(Talk, blank=True, null=True, on_delete=models.CASCADE)
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
    sponsor = models.ForeignKey(Sponsor, blank=True, null=True, on_delete=models.CASCADE)
    video = models.CharField(max_length=1000, blank=True)

    bookable = models.BooleanField(default=False)
    seats = models.PositiveIntegerField(
        default=0,
        help_text='seats available. Override the track default if set')

    objects = EventManager()

    class Meta:
        ordering = ['start_time']

    def __str__(self):
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
    
        """ Return time range of the event in local time.
        
        """
        n = datetime.datetime.combine(self.schedule.date, self.start_time)
        return (
            n, (n + datetime.timedelta(seconds=self.get_duration() * 60))
        )

    def get_utc_start_datetime(self):

        """ Return start time as datetime in UTC.
        
        """
        dt = datetime.datetime.combine(self.schedule.date, self.start_time)
        return dt.astimezone(datetime.timezone.utc)

    def get_utc_end_datetime(self):
    
        """ Return end time as datetime in UTC.
        
        """
        return self.get_utc_start_datetime() + datetime.timedelta(
            seconds=self.get_duration() * 60)

    def get_schedule_string(self):
    
        """ Return a text representation of the scheduled slot.
        
        """
        (start, end) = self.get_time_range()
        duration = self.get_duration()
        tz = pytz.timezone(settings.TIME_ZONE)
        end = tz.localize(end)
        return (
            f'{start.strftime("%a, %b %d, %H:%M")}-'
            f'{end.strftime("%H:%M %Z")} ({duration} min)'
            )

    def get_description(self):
        if self.talk:
            return self.talk.title
        else:
            return self.custom

    def get_all_track_names(self):

        """ Return a set of internal track names to which this event applies.

        """
        return set(track.track for track in self.tracks.all())

    def json_dump(self):

        (start, end) = self.get_time_range()
        return {
            'custom_description': self.custom,
            'custom_abstract': self.abstract,
            'start_time': self.start_time.isoformat(),
            'duration': self.get_duration(),
            'time_range': (start.isoformat(), end.isoformat()),
            'track_names': list(self.get_all_track_names()),
            }

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
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('track', 'event',),)


class VotoTalk(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    talk = models.ForeignKey(Talk, on_delete=models.CASCADE)
    vote = models.DecimalField(max_digits=5, decimal_places=2)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        unique_together = (('user', 'talk'),)
        verbose_name = 'Talk voting'
        verbose_name_plural = 'Talk votings'


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


# ========================================
# NEWS
# TODO: split conference/models.py to multiple files and put it this model in a
# separate file.
# ========================================


class News(TimeStampedModel):

    STATUS = Choices(
        (0, 'DRAFT', 'Draft'),
        (10, 'PUBLISHED', 'Published'),
        (20, 'DELETED', 'Deleted'),
    )

    # CharField because sqlite
    uuid = models.CharField(unique=True, max_length=40, default=uuid.uuid4)

    conference = models.ForeignKey(Conference, on_delete=models.deletion.PROTECT)
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    content = models.TextField()

    status = models.PositiveIntegerField(choices=STATUS, default=STATUS.DRAFT)
    published_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'News'
        ordering = ['-published_date']

    def __str__(self):
        return self.title


# ========================================
# StripePayment
# TODO: split conference/models.py to multiple files and put it this model in a
# separate file.
# ========================================


class StripePayment(models.Model):

    STATUS_CHOICES = Choices(
        ('NEW', 'New'),
        ('SUCCESSFUL', 'Successful'),
        ('FAILED', 'Failed'),
    )

    uuid = models.CharField(max_length=40, unique=True, default=uuid.uuid4)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    token = models.CharField(max_length=100)
    token_type = models.CharField(max_length=20)
    charge_id = models.CharField(max_length=100, null=True)
    session_id = models.CharField(max_length=100, null=True)
    email = models.CharField(max_length=255)

    user = models.ForeignKey(get_user_model(), on_delete=models.deletion.PROTECT)
    order = models.ForeignKey('assopy.Order', on_delete=models.deletion.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    message = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return f'StripePayment(uuid={self.uuid}, status={self.status})'

    def amount_for_stripe(self):
        # 9.99 becomes 999
        return int(self.amount * 100)

### Streaming

STREAMS_HELP_TEXT = """Stream definitions as JSON list, with one entry per track in
the stream set. Order is important. The stream page will default to showing the first
track. Example:
[
    {
        "title": "Holy Grail",
        "fare_codes": ["TRCC", "TRCP", "TRSC", "TRSP", "TRVC", "TRVP"],
        "url": "https://www.youtube.com/embed/EEIk7gwjgIM"
    }
]
"""
class StreamSet(models.Model):

    conference = models.ForeignKey(Conference, on_delete=models.deletion.PROTECT)
    name = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True, help_text="Is this set visible to enduser?")
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    # JSON list with the stream descritions:
    #   - title: Title of the track
    #   - fare_codes: List of fare codes which may see the stream
    #   - url: YouTube/Vimeo Stream URL
    streams = JSONField(blank=True, help_text=STREAMS_HELP_TEXT)

