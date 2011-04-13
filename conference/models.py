# -*- coding: UTF-8 -*-
import datetime
import os
import os.path
import subprocess

from django.conf import settings as dsettings
from django.core import exceptions
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

import conference
import conference.gmap
from conference import settings

class ConferenceManager(models.Manager):
    def current(self):
        return self.get(code=settings.CONFERENCE)

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
            language = dsettings.LANGUAGE_CODE
        object_type = ContentType.objects.get_for_model(object)
        try:
            mc = self.get(content_type=object_type, object_id=object.id, content=content, language=language)
        except MultilingualContent.DoesNotExist:
            mc = MultilingualContent(content_object=object)
            mc.content = content
            mc.language = language
        mc.body = body
        mc.save()

    def getContent(self, object, content, language):
        if language is None:
            language = dsettings.LANGUAGE_CODE
        object_type = ContentType.objects.get_for_model(object)
        records = dict(
            (x.language, x)
            for x in self.exclude(body='').filter(content_type=object_type, object_id=object.id, content=content)
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
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    language = models.CharField(max_length = 3)
    content = models.CharField(max_length = 20)
    body = models.TextField()

    objects = MultilingualContentManager()

import urlparse
from django.core.files.storage import FileSystemStorage

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

class SpeakerManager(models.Manager):
    def createFromName(self, name, user=None):
        """
        Crea uno speaker, collegandolo all'utente passato, calcolando uno slug
        univoco per il nome passato.
        """
        slug = slugify(name)
        speaker = Speaker()
        cursor = connection.cursor()
        # qui ho bisogno di impedire che altre connessioni possano leggere il
        # db fino a quando non ho finito
        cursor.execute('BEGIN EXCLUSIVE TRANSACTION')
        # È importante assicurarsi che la transazione venga chiusa, con successo
        # o fallimento, il prima possibile
        try:
            count = 0
            check = slug
            while True:
                if self.filter(slug=check).count() == 0:
                    break
                count += 1
                check = '%s-%d' % (slug, count)
            speaker.name = name
            speaker.slug = check
            speaker.user = user
            speaker.save()
        except:
            transaction.rollback()
            raise
        else:
            transaction.commit()
        return speaker

SPEAKER_INDUSTRY = (
    ('alimentare',      'Alimentare'),
    ('ambiente',        'Ambiente e Sicurezza'),
    ('automazione',     'Automazione'),
    ('automotive',      'Automotive'),
    ('bancario',        'Bancario e Assicurativo'),
    ('comunicazione',   'Comunicazione'),
    ('commercio',       'Commercio'),
    ('consulting',      'Consulting'),
    ('editoria',        'Editoria'),
    ('elettronica',     'Elettronica'),
    ('energia',         'Energia'),
    ('farmaceutica',    'Farmaceutica'),
    ('industria',       'Industria (chimica, meccanica, edile)'),
    ('informatica',     'Informatica e Software'),
    ('media',           'Intrattenimento e Media'),
    ('istruzione',      'Istruzione'),
    ('luxury',          'Luxury (Moda, Gioielli)'),
    ('tessile',         'Tessile (Abbigliamento, Pelletteria, Accessori)'),
    ('pubblica-amm',    'Pubblica Amministrazione'),
    ('telecom',         'Telecomunicazioni'),
    ('trasporti',       'Trasporti'),
    ('turismo',         'Turismo'),
    ('altro',           'Altro'),
)
class Speaker(models.Model, UrlMixin):
    user = models.OneToOneField('auth.User', null=True)
    name = models.CharField('nome e cognome speaker', max_length=100)
    slug = models.SlugField()
    homepage = models.URLField(verify_exists=False, blank=True)
    activity = models.CharField(max_length=50, blank=True)
    activity_homepage = models.URLField(verify_exists=False, blank=True)
    company = models.CharField(max_length=50, blank=True)
    company_homepage = models.URLField(verify_exists=False, blank=True)
    industry = models.CharField(max_length=50, choices=SPEAKER_INDUSTRY, blank=True)
    location = models.CharField(max_length=100, blank=True)
    twitter = models.CharField(max_length=80, blank=True)
    image = models.ImageField(upload_to=_fs_upload_to('speaker'), blank=True)
    bios = generic.GenericRelation(MultilingualContent)
    ad_hoc_description = generic.GenericRelation(MultilingualContent, related_name='ad_hoc_description_set', verbose_name='descrizione ad hoc')
    previous_experience = models.TextField(blank=True)
    last_year_talks = models.PositiveIntegerField(default=0)
    max_audience = models.PositiveIntegerField(default=0)
    video_presentation = models.TextField(blank=True)

    objects = SpeakerManager()

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('conference-speaker', (), { 'slug': self.slug })

    get_url_path = get_absolute_url

    def setBio(self, body, language=None):
        MultilingualContent.objects.setContent(self, 'bios', language, body)

    def getBio(self, language=None):
        return MultilingualContent.objects.getContent(self, 'bios', language)

    def setAdHocDescription(self, body, language=None):
        MultilingualContent.objects.setContent(self, 'ad_hoc_description', language, body)

    def getAdHocDescription(self, language=None):
        return MultilingualContent.objects.getContent(self, 'ad_hoc_description', language)

    def talks(self, conference=None, include_secondary=True, status=None):
        """
        Restituisce i talk dello speaker filtrandoli per conferenza (se non
        None); se include_secondary è True vengono inclusi anche i talk dove
        non è lo speaker principale. Se status è diverso da None vengono
        ritornati solo i talk con lo stato richiesto.
        """
        if status is None:
            m = 'all'
        elif status in ('proposed', 'accepted'):
            m = status
        else:
            raise ValueError('status unknown')
        qs = getattr(self.talk_set, m)()
        if include_secondary:
            qs |= getattr(self.additional_speakers, m)()
        if conference is not None:
            qs = qs.filter(conference=conference)
        return qs

post_save.connect(postSaveResizeImageHandler, sender=Speaker)

TALK_DURATION = (
    (5,   _('5 minutes')),
    (10,  _('10 minutes')),
    (15,  _('15 minutes')),
    (25,  _('25 minutes')),
    (30,  _('30 minutes')),
    (40,  _('40 minutes')),
    (45,  _('45 minutes')),
    (60,  _('60 minutes')),
    (90,  _('90 minutes')),
    (120, _('120 minutes')),
)
TALK_LANGUAGES = (
    ('it', _('Italian')),
    ('en', _('English')),
)
TALK_STATUS = (
    ('proposed', _('Proposed')),
    ('accepted', _('Accepted')),
)

VIDEO_TYPE = (
    ('viddler_oembed', 'Viddler (oEmbed)'),
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

    def createFromTitle(self, title, conference, speaker, status='proposed', duration=30, language='en', level='beginner', training_available=False):
        slug = slugify(title)
        talk = Talk()
        talk.title = title
        talk.conference = conference
        talk.status = status
        talk.duration = duration
        talk.language = language
        talk.level = level
        talk.training_available = training_available
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
            talk.speakers.add(speaker)
        except:
            transaction.rollback()
            raise
        else:
            transaction.commit()
        return talk

TALK_TYPE = (
    ('s', 'Standard'),
    ('i', 'Interactive'),
)
class Talk(models.Model, UrlMixin):
    title = models.CharField('titolo del talk', max_length=100)
    slug = models.SlugField(max_length=100)
    conference = models.CharField(help_text='nome della conferenza', max_length=20)
    speakers = models.ManyToManyField(Speaker)
    additional_speakers = models.ManyToManyField(Speaker, related_name='additional_speakers', blank=True)
    duration = models.IntegerField(choices=TALK_DURATION)
    language = models.CharField('lingua del talk', max_length=3, choices=TALK_LANGUAGES)
    abstracts = generic.GenericRelation(MultilingualContent)
    slides = models.FileField(upload_to=_fs_upload_to('slides'), blank=True)
    video_type = models.CharField(max_length=30, choices=VIDEO_TYPE, blank=True)
    video_url = models.TextField(blank=True)
    video_file = models.FileField(upload_to=_fs_upload_to('videos'), blank=True)
    promo_video_url = models.TextField(blank=True)
    status = models.CharField(max_length=8, choices=TALK_STATUS)
    level = models.CharField(max_length=12, choices=TALK_LEVEL)
    training_available = models.BooleanField(default=False)
    type = models.CharField(max_length=1, choices=TALK_TYPE, default='s')
    # Questi sono i tag che lo speaker suggerisce per il proprio talk, li ho
    # messi qui per una questione di tempo (il cfp di BSW2011 incombe) ma la
    # cosa giusta sarebbe creare un nuovo modello "Submission" legato al Talk e
    # mettere li i dati del cfp
    suggested_tags = models.CharField(max_length=100, blank=True)
    tags = TagField()
    created = models.DateTimeField(auto_now_add=True)

    objects = TalkManager()

    class Meta:
        ordering = ['title']

    def __unicode__(self):
        return '(%s) %s [%s]' % (self.duration, self.title, self.conference)

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
        return (self.speakers.all() | self.additional_speakers.all()).distinct()

    def setAbstract(self, body, language=None):
        MultilingualContent.objects.setContent(self, 'abstracts', language, body)

    def getAbstract(self, language=None):
        return MultilingualContent.objects.getContent(self, 'abstracts', language)

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
    ticket_type = models.CharField(max_length=10, choices=FARE_TICKET_TYPES, default='conference')
    payment_type = models.CharField(max_length=1, choices=FARE_PAYMENT_TYPE, default='p')
    blob = models.TextField(blank=True)

    objects = FareManager()

    def __unicode__(self):
        return '%s - %s' % (self.code, self.conference)

    class Meta:
        ordering = ('conference', 'code')
        unique_together = (('conference', 'code'),)

    def valid(self):
        today = datetime.date.today()
        return self.start_validity <= today <= self.end_validity

class TicketManager(models.Manager):
    def get_query_set(self):
        return self._QuerySet(self.model)

    def __getattr__(self, name):
        return getattr(self.all(), name)

    class _QuerySet(QuerySet):
        def conference(self, conference):
            return self.filter(fare__conference=conference)

class Ticket(models.Model):
    user = models.ForeignKey('auth.User', help_text='holder of the ticket (who has buyed it?)')
    name = models.CharField(max_length=60, blank=True, help_text='Real name of the attendee.<br />This is the person that will attend the conference.')
    fare = models.ForeignKey(Fare)

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

class Track(models.Model):
    schedule = models.ForeignKey(Schedule)
    track = models.CharField('nome track', max_length = 20)
    title = models.TextField('titolo della track', help_text = 'HTML supportato')
    order = models.PositiveIntegerField('ordine', default = 0)
    translate = models.BooleanField(default = False)

    class Meta:
        ordering = ['order']

    def __unicode__(self):
        return self.track

class Event(models.Model):
    schedule = models.ForeignKey(Schedule)
    talk = models.ForeignKey(Talk, blank = True, null = True)
    custom = models.TextField(blank = True)
    start_time = models.TimeField()
    track = TagField(help_text = 'Inserire uno o più nomi di track, oppure "keynote"')
    sponsor = models.ForeignKey(Sponsor, blank = True, null = True)

    class Meta:
        ordering = ['start_time']

    def __unicode__(self):
        if self.talk:
            return '%s - %smin' % (self.talk.title, self.talk.duration)
        else:
            return self.custom

    def get_track(self):
        """
        ritorna la prima istanza di track tra quelle specificate o None se l'evento
        è di tipo speciale
        """
        dbtracks = dict( (t.track, t) for t in self.schedule.track_set.all())
        for t in tagging.models.Tag.objects.get_for_object(self):
            if t.name in dbtracks:
                return dbtracks[t.name]

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

