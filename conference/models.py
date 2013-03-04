# -*- coding: UTF-8 -*-
import datetime
import os
import os.path
import subprocess
from collections import defaultdict

from django.conf import settings as dsettings
from django.core import exceptions
from django.core.cache import cache
from django.db import connection
from django.db import models
from django.db import transaction
from django.db.models.query import QuerySet
from django.db.models.signals import post_save
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _

from django_urls import UrlMixin

import tagging
from tagging.fields import TagField
from tagging.utils import parse_tag_input

import conference
import conference.gmap
from conference import settings

from taggit.models import TagBase, GenericTaggedItemBase, ItemBase
from taggit.managers import TaggableManager

# ConferenceTag e ConferenceTaggedItem servono per creare un "namespace" per i
# tag relativi a conference. In questo modo non devo preocuparmi di altri
# utilizzi di taggit fatti da altre app.
class ConferenceTagManager(models.Manager):
    def get_query_set(self):
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
            # prima di salvare questo tag mi assicuro che non ne esista un
            # altro diverso solo per maiuscole/minuscole
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
        key = 'CONFERENCE_CURRENT'
        data = cache.get(key)
        if data is None:
            data = self.get(code=settings.CONFERENCE)
            # mantengo in cache abbastanza a lungo perchè la query non sia più
            # un problema
            cache.set(key, data, 60*60*24*7)
        return data

    @classmethod
    def clear_cache(cls, sender, **kwargs):
        cache.delete('CONFERENCE_CURRENT')

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
                raise exceptions.ValidationError('range di date per la conferenza non valido') 
        if self.cfp_start and self.cfp_end:
            if self.cfp_start > self.cfp_end:
                raise exceptions.ValidationError('range di date per il cfp non valido') 
        if self.voting_start and self.voting_end:
            if self.voting_start > self.voting_end:
                raise exceptions.ValidationError('range di date per la votazione non valido') 

    def cfp(self):
        today = datetime.date.today()
        try:
            return self.cfp_start <= today <= self.cfp_end
        except TypeError:
            # date non impostate
            return False

    def voting(self):
        today = datetime.date.today()
        try:
            return self.voting_start <= today <= self.voting_end
        except TypeError:
            # date non impostate
            return False

    def conference(self):
        today = datetime.date.today()
        try:
            return self.conference_start <= today <= self.conference_end
        except TypeError:
            raise
            # date non impostate
            return False

post_save.connect(ConferenceManager.clear_cache, sender=Conference)

class DeadlineManager(models.Manager):
    def valid_news(self):
        today = datetime.date.today()
        return self.all().filter(date__gte = today)

class Deadline(models.Model):
    """
    deadline per il pycon
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
        Ritorna il DeadlineContent nella lingua specificata.  Se il
        DeadlineContent non esiste e fallback è False viene sollevata
        l'eccezione ObjectDoesNotExist. Se fallback è True viene ritornato il
        primo DeadlineContent disponibile.
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
    Testo, multilingua, di una deadline
    """
    deadline = models.ForeignKey(Deadline)
    language = models.CharField(max_length=3)
    headline = models.CharField(max_length=200)
    body = models.TextField()

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

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
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    language = models.CharField(max_length = 3)
    content = models.CharField(max_length = 20)
    body = models.TextField()

    objects = MultilingualContentManager()

def _fs_upload_to(subdir, attr=None, package='conference'):
    if attr is None:
        attr = lambda i: i.slug
    def wrapper(instance, filename):
        fpath = os.path.join(package, subdir, '%s%s' % (attr(instance), os.path.splitext(filename)[1].lower()))
        ipath = os.path.join(dsettings.MEDIA_ROOT, fpath)
        if os.path.exists(ipath):
            os.unlink(ipath)
        return fpath
    return wrapper

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
                    # l'if mi tutela da slug del tipo "str-str-str"
                    last = 0
                continue
            if counter > last:
                last = counter

        if last is not None:
            slug = '%s-%d' % (slug, last+1)
        elif not slug:
            # slug può essere una stringa vuota solo se lo user ha nome e
            # cognome vuoti e se è il primo con questa anomalia.
            # impostando lo slug a "-1" risolvo la situazione anche per i
            # successivi che trovando un precedente continueranno la sequenza
            slug = '-1'
        return slug

    def randomUUID(self, length=6):
        import string
        import random
        return ''.join(random.sample(string.letters + string.digits, length))

    # TODO: usare i savepoint. Ricordarsi che, almeno fino a django 1.4, il
    # backend sqlite non supporta i savepoint nonostante sqlite lo faccia da
    # tempo, quindi si deve passare da cursor.execute(); se mai passeremo a
    # postgres ricordarsi di fare rollback del savepoint nell'except (o
    # impostare l'autocommit)
    def getOrCreateForUser(self, user):
        """
        Ritorna o crea il profilo associato all'utente.
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
            except IntegrityError, e:
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
    È il profilo di un partecipante (inclusi gli speaker) alla conferenza, il
    collegamento con la persona è ottenuto tramite la foreign key verso
    auth.User.
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

    personal_homepage = models.URLField(_('Personal homepage'), verify_exists=False, blank=True)
    company = models.CharField(_('Company'), max_length=50, blank=True)
    company_homepage = models.URLField(_('Company homepage'), verify_exists=False, blank=True)
    job_title = models.CharField(_('Job title'), max_length=50, blank=True)

    location = models.CharField(_('Location'), max_length=100, blank=True)
    bios = generic.GenericRelation(MultilingualContent)

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
    Presenza di un partecipante ad una conferenza.
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
    Collegamento tra due partecipanti
    """
    attendee1 = models.ForeignKey(AttendeeProfile, related_name='link1')
    attendee2 = models.ForeignKey(AttendeeProfile, related_name='link2')
    message = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    objects = AttendeeLinkManager()

class SpeakerManager(models.Manager):
    def byConference(self, conf, only_accepted=True, talk_type=None):
        """
        Ritorna tutti gli speaker della conferenza
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
        Restituisce i talk dello speaker filtrandoli per conferenza (se non
        None); se include_secondary è True vengono inclusi anche i talk dove
        non è lo speaker principale. Se status è diverso da None vengono
        ritornati solo i talk con lo stato richiesto.
        """
        qs = TalkSpeaker.objects.filter(speaker=self)
        if status in ('proposed', 'accepted'):
            qs = qs.filter(talk__status=status)
        elif status is not None:
            raise ValueError('status unknown')
        if not include_secondary:
            qs = qs.filter(helper=False)
        if conference is not None:
            qs = qs.filter(talk__conference=conference)
        return Talk.objects.filter(id__in=qs.values('talk'))

TALK_DURATION = settings.TALK_DURATION
TALK_LANGUAGES = (
    ('it', _('Italian')),
    ('en', _('English')),
)
TALK_STATUS = (
    ('proposed', _('Proposed')),
    ('accepted', _('Accepted')),
)

VIDEO_TYPE = (
    ('viddler_oembed', 'oEmbed (Youtube, Vimeo, ...)'),
    ('download', 'Download'),
)

TALK_LEVEL = (
    ('beginner',     _('Beginner')),
    ('intermediate', _('Intermediate')),
    ('advanced',     _('Advanced')),
)

class TalkManager(models.Manager):
    def get_query_set(self):
        return self._QuerySet(self.model)

    def __getattr__(self, name):
        return getattr(self.all(), name)

    class _QuerySet(QuerySet):
        def proposed(self, conference=None):
            qs = self.filter(status='proposed')
            if conference:
                qs = qs.filter(conference=conference)
            return qs
        def accepted(self, conference=None):
            qs = self.filter(status='accepted')
            if conference:
                qs = qs.filter(conference=conference)
            return qs

    def createFromTitle(self, title, conference, speaker, status='proposed', duration=30, language='en', level='beginner', training_available=False, type='s'):
        slug = slugify(title)
        talk = Talk()
        talk.title = title
        talk.conference = conference
        talk.status = status
        talk.duration = duration
        talk.language = language
        talk.level = level
        talk.training_available = training_available
        talk.type = type
        cursor = connection.cursor()
        cursor.execute('BEGIN EXCLUSIVE TRANSACTION')
        try:
            count = 0
            check = slug
            while True:
                if self.filter(slug=check).count() == 0:
                    break
                count += 1
                check = '%s-%d' % (slug, count)
            talk.slug = check
            talk.save()
            # associo qui lo speaker così se c'è qualche problema, ad esempio
            # lo speaker non è valido, il tutto avviene in una transazione ed
            # il db rimane pulito.
            TalkSpeaker(talk=talk, speaker=speaker).save()
        except:
            transaction.rollback()
            raise
        else:
            transaction.commit()
        return talk

TALK_TYPE = (
    ('s', 'Talk'),
    ('i', 'Interactive'),
    ('t', 'Training'),
    ('p', 'Poster session'),
    ('h', 'Help desk'),
)
class Talk(models.Model, UrlMixin):
    title = models.CharField(_('Talk title'), max_length=100)
    slug = models.SlugField(max_length=100)
    conference = models.CharField(help_text='nome della conferenza', max_length=20)
    speakers = models.ManyToManyField(Speaker, through='TalkSpeaker')
    # durata totale del talk (include la sessione di Q&A)
    duration = models.IntegerField(
        _('Suggested duration'),
        choices=TALK_DURATION,
        help_text=_('This is the <b>net duration</b> of the talk, excluding Q&A'))
    # durata della sessione di Q&A
    qa_duration = models.IntegerField(
        _('Q&A duration'),
        default=0)
    language = models.CharField(_('Language'), max_length=3, choices=TALK_LANGUAGES)
    abstracts = generic.GenericRelation(
        MultilingualContent,
        verbose_name=_('Talk abstract'),
        help_text=_('<p>Please enter a short description of the talk you are submitting. Be sure to includes the goals of your talk and any prerequisite required to fully understand it.</p><p>Suggested size: two or three paragraphs.</p>'))
    slides = models.FileField(upload_to=_fs_upload_to('slides'), blank=True)
    video_type = models.CharField(max_length=30, choices=VIDEO_TYPE, blank=True)
    video_url = models.TextField(blank=True)
    video_file = models.FileField(upload_to=_fs_upload_to('videos'), blank=True)
    teaser_video = models.URLField(
        _('Teaser video'),
        verify_exists=False,
        blank=True,
        help_text=_('Insert the url for your teaser video'))
    status = models.CharField(max_length=8, choices=TALK_STATUS)
    level = models.CharField(
        _('Audience level'),
        default='beginner',
        max_length=12,
        choices=TALK_LEVEL)
    training_available = models.BooleanField(default=False)
    type = models.CharField(max_length=1, choices=TALK_TYPE, default='s')
    # Questi sono i tag che lo speaker suggerisce per il proprio talk, li ho
    # messi qui per una questione di tempo (il cfp di BSW2011 incombe) ma la
    # cosa giusta sarebbe creare un nuovo modello "Submission" legato al Talk e
    # mettere li i dati del cfp
    suggested_tags = models.CharField(max_length=100, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    tags = TaggableManager(through=ConferenceTaggedItem)
    objects = TalkManager()

    class Meta:
        ordering = ['title']

    def __unicode__(self):
        return '%s [%s][%s][%s]' % (self.title, self.conference, self.language, self.duration)

    @models.permalink
    def get_absolute_url(self):
        return ('conference-talk', (), { 'slug': self.slug })

    get_url_path = get_absolute_url

    def get_event(self):
        try:
            return self.event_set.all()[0]
        except IndexError:
            return None

    def get_all_speakers(self):
        return self.speakers.all().select_related('speaker')

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
    def get_query_set(self):
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

FARE_TICKET_TYPES = (
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
    conference = models.CharField(help_text='codice della conferenza', max_length=20)
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    start_validity = models.DateField(null=True)
    end_validity = models.DateField(null=True)
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
        today = datetime.date.today()
        return self.start_validity <= today <= self.end_validity

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
        """
        Crea e ritorna i biglietti associati a questa tariffa.
        Normalmente ogni tariffa comporta un solo biglietto, ma questo
        comportamento è modificabile da un listener collegato al segnale
        fare_tickets.

        Le istanze ritornate da questo metodo hanno un attributo aggiuntivo
        `fare_description` (volatile) che riporta una descrizione della tariffa
        specifica per il singolo biglietto.
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
    def get_query_set(self):
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
    user = models.ForeignKey('auth.User', help_text='holder of the ticket (who has buyed it?)')
    name = models.CharField(max_length=60, blank=True, help_text='Real name of the attendee.<br />This is the person that will attend the conference.')
    fare = models.ForeignKey(Fare)
    frozen = models.BooleanField(default=False)
    ticket_type = models.CharField(max_length=8, choices=TICKET_TYPE, default='standard')

    objects = TicketManager()

    def __unicode__(self):
        return 'Ticket "%s" (%s)' % (self.fare.name, self.fare.code)

class Sponsor(models.Model):
    """
    Attraverso l'elenco di SponsorIncome un'istanza di Sponsor è collegata
    con le informazioni riguardanti tutte le sponsorizzazioni fatte.
    Sempre in SponsorIncome la conferenza è indicata, come in altri posti,
    con una chiave alfanumerica non collegata a nessuna tabella.
    """
    sponsor = models.CharField(max_length=100, help_text='nome dello sponsor')
    slug = models.SlugField()
    url = models.URLField(verify_exists=False, blank=True)
    logo = models.ImageField(
        upload_to=_fs_upload_to('sponsor'), blank=True,
        help_text='Inserire un immagine raster sufficientemente grande da poter essere scalata al bisogno'
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
    I media partner sono degli sponsor che non pagano ma che offrono visibilità
    di qualche tipo.
    """
    partner = models.CharField(max_length=100, help_text='nome del media partner')
    slug = models.SlugField()
    url = models.URLField(verify_exists=False, blank=True)
    logo = models.ImageField(
        upload_to=_fs_upload_to('media-partner'), blank = True,
        help_text='Inserire un immagine raster sufficientemente grande da poter essere scalata al bisogno'
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
        restituisce il numero di partecipanti per ogni schedule della conferenza.
        """
        return settings.SCHEDULE_ATTENDEES(conference, forecast)

    def events_score_by_attendance(self, conference):
        """
        Utilizzandoi gli EventInterest ritorna un "punteggio di presenza" per
        ogni evento; Il punteggio è proporzionale al numero di persone che
        hanno esspresso interesse in quell'evento.
        """
        # Considero una manifestazione di interesse, interest > 0, come la
        # volontà di partecipare ad un evento e aggiungo l'utente tra i
        # partecipanti. Se l'utente ha "votato" più eventi contemporanei
        # considero la sua presenza in proporzione (quindi gli eventi potranno
        # avere "punteggio" frazionario)
        events = defaultdict(set)
        for x in EventInterest.objects\
                    .filter(event__schedule__conference=conference, interest__gt=0)\
                    .select_related('event__schedule'):
            events[x.event].add(x.user_id)
        # Oltre agli EventInterest tengo conto anche degli EventBooking, la
        # confidenza in questi casi è ancora maggiore
        for x in EventBooking.objects\
                    .filter(event__schedule__conference=conference)\
                    .select_related('event__schedule'):
            events[x.event].add(x.user_id)

        # associo ad ogni evento il numero di voti che ha ottenuto;
        # l'operazione è complicata dal fatto che non tutti i voti hanno lo
        # stesso peso; se un utente ha marcato come +1 due eventi che avvengano
        # in parallelo ovviamente non potrà partecipare ad entrambi, quindi il
        # suo voto deve essere scalato
        scores = defaultdict(lambda: 0.0)
        for evt, users in events.items():
            group = list(Event.objects.group_events_by_times(events, event=evt))[0]
            while users:
                u = users.pop()
                # Quanto vale la presenza di `u` per l'evento `evt`?  Se
                # `u` non partecipa a nessun'altro evento dello stesso
                # gruppo allora 1, altrimenti un valore proporzionale al
                # numero di eventi che gli interesssano.
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

    def expected_attendance(self, conference, factor=0.95):
        """
        restituisce per ogni evento la previsione di partecipazione basata
        sugli EventInterest.
        """
        seats_available = defaultdict(lambda: 0)
        for row in EventTrack.objects\
                    .filter(event__schedule__conference='ep2012')\
                    .values('event', 'track__seats'):
            seats_available[row['event']] += row['track__seats']

        scores = self.events_score_by_attendance(conference)
        events = Event.objects\
            .filter(schedule__conference=conference)\
            .select_related('schedule')

        output = {}
        # adesso devo fare la previsione dei partecipanti per ogni evento, per
        # farla divido il punteggio di un evento per il numero di votanti che
        # hanno espresso un voto per un evento *nella medesima fascia
        # temporale*; il numero che ottengo è un fattore k che se moltiplicato
        # per la previsione di presenze al giorno mi da un'indicazione di
        # quante persone sono previste per l'evento.
        forecasts = self.attendees(conference, forecast=True)

        # per calcolare il punteggio relativo ad una fascia temporale devo fare
        # un doppio for sugli eventi, per limitare il numero delle iterazioni
        # interno raggruppo gli eventi per giorno
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
    Direttamente dentro lo schedule abbiamo l'indicazione della conferenza,
    una campo alfanumerico libero, e il giorno a cui si riferisce.

    Attraverso le ForeignKey lo schedule è collegato alle track e agli
    eventi.

    Questi ultimi possono essere dei talk o degli eventi "custom", come la
    pyBirra, e sono collegati alle track in modalità "weak", attraverso un
    tagfield.
    """
    conference = models.CharField(help_text = 'nome della conferenza', max_length = 20)
    slug = models.SlugField()
    date = models.DateField()
    description = models.TextField(blank=True)

    objects = ScheduleManager()

    class Meta:
        ordering = ['date']

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
        Raggruppa gli eventi, ovviamente appartenenti a track diverse, che
        si "accavvallano" temporalmente.

        Rtorna un generatore che ad ogni iterazione restituisce un gruppo(list)
        di eventi.
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
        ritorna la prima istanza di track tra quelle specificate o None se l'evento
        è di tipo speciale
        """
        # XXX: utilizzare il template tag get_event_track che cacha la query 
        dbtracks = dict( (t.track, t) for t in self.schedule.track_set.all())
        for t in tagging.models.Tag.objects.get_for_object(self):
            if t.name in dbtracks:
                return dbtracks[t.name]

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
        return e

    def cancel_reservation(self, eid, uid):
        EventBooking.objects.filter(event=eid, user=uid).delete()

class EventBooking(models.Model):
    event = models.ForeignKey(Event)
    user = models.ForeignKey('auth.User')

    objects = EventBookingManager()

    class Meta:
        unique_together = (('user', 'event'),)

class Hotel(models.Model):
    """
    Gli hotel permettono di tenere traccia dei posti convenzionati e non dove
    trovare alloggio durante la conferenza.
    """
    name = models.CharField('nome dell\'hotel', max_length = 100)
    telephone = models.CharField('contatti telefonici', max_length = 50, blank = True)
    url = models.URLField(verify_exists = False, blank = True)
    email = models.EmailField('email', blank = True)
    availability = models.CharField('Disponibilità', max_length = 50, blank = True)
    price = models.CharField('Prezzo', max_length = 50, blank = True)
    note = models.TextField('note', blank = True)
    affiliated = models.BooleanField('convenzionato', default = False)
    visible = models.BooleanField('visibile', default = True)
    address = models.CharField('indirizzo', max_length = 200, default = '', blank = True)
    lng = models.FloatField('longitudine', default = 0.0, blank = True)
    lat = models.FloatField('latitudine', default = 0.0, blank = True)
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
    name = models.CharField('nome', max_length = 100)
    address = models.CharField('indirizzo', max_length = 200, default = '', blank = True)
    type = models.CharField(max_length = 10, choices=SPECIAL_PLACE_TYPES)
    url = models.URLField(verify_exists = False, blank = True)
    email = models.EmailField('email', blank = True)
    telephone = models.CharField('contatti telefonici', max_length = 50, blank = True)
    note = models.TextField('note', blank = True)
    visible = models.BooleanField('visibile', default = True)
    lng = models.FloatField('longitudine', default = 0.0, blank = True)
    lat = models.FloatField('latitudine', default = 0.0, blank = True)

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
    Lo sai che?
    """
    visible = models.BooleanField('visible', default = True)
    messages = generic.GenericRelation(MultilingualContent)

class Quote(models.Model):
    who = models.CharField(max_length=100)
    conference = models.CharField(max_length=20)
    text = models.TextField()
    activity = models.CharField(max_length=50, blank=True)
    image = models.ImageField(upload_to=_fs_upload_to('quote', attr=lambda i: slugify(i.who)), blank=True)

    class Meta:
        ordering = ['conference', 'who']

class VotoTalk(models.Model):
    user = models.ForeignKey('auth.User')
    talk = models.ForeignKey(Talk)
    vote = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = (('user', 'talk'),)
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
