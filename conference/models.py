# -*- coding: UTF-8 -*-
import datetime
import os.path
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save

import tagging
from tagging.fields import TagField

import conference
import conference.gmap
import subprocess

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

class DeadlineContent(models.Model):
    """
    Testo, multilingua, di una deadline
    """
    deadline = models.ForeignKey(Deadline)
    language = models.CharField(max_length = 3)
    body = models.TextField()

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

class MultilingualContent(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    language = models.CharField(max_length = 3)
    content = models.CharField(max_length = 20)
    body = models.TextField()

import urlparse
from django.core.files.storage import FileSystemStorage

# definisco uno storage custom perché non uso MEDIA_DIR per memorizzare la
# roba sotto stuff

def _build_fs_stuff(subdir):
    fs = FileSystemStorage(
        location = os.path.join(settings.STUFF_DIR, subdir),
        base_url = urlparse.urljoin(settings.MEDIA_URL, 'stuff/%s/' % subdir)
    )

    def build_path(instance, filename):
        fname = instance.slug + os.path.splitext(filename)[1].lower()
        fs.delete(fname)
        return fname

    return fs, build_path

fs_speaker, _speaker_image_path = _build_fs_stuff('speaker')

class Speaker(models.Model):
    name = models.CharField('nome e cognome speaker', max_length = 100)
    slug = models.SlugField()
    homepage = models.URLField(verify_exists = False, blank = True)
    activity = models.CharField(max_length = 50, blank = True)
    industry = models.CharField(max_length = 50, blank = True)
    location = models.CharField(max_length = 100, blank = True)
    image = models.ImageField(upload_to = _speaker_image_path, blank = True, storage = fs_speaker)
    bios = generic.GenericRelation(MultilingualContent)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('conference-speaker', (), { 'slug': self.slug })

TALK_DURATION = (
    (30, '30 minuti'),
    (45, '45 minuti'),
    (60, '60 minuti'),
    (90, '90 minuti'),
    (120, '120 minuti'),
)
TALK_LANGUAGES = (
    ('it', 'Italiano'),
    ('en', 'Inglese'),
)

fs_slides, _talk_slides_path = _build_fs_stuff('slides')

class Talk(models.Model):
    title = models.CharField('titolo del talk', max_length = 100)
    slug = models.SlugField()
    conference = models.CharField(help_text = 'nome della conferenza', max_length = 20)
    speakers = models.ManyToManyField(Speaker)
    duration = models.IntegerField(choices = TALK_DURATION)
    language = models.CharField('lingua del talk', max_length = 3, choices = TALK_LANGUAGES)
    abstracts = generic.GenericRelation(MultilingualContent)
    slides = models.FileField(upload_to = _talk_slides_path, blank = True, storage = fs_slides)
    video = models.CharField(max_length = 200, blank = True)
    tags = TagField()

    class Meta:
        ordering = ['title']

    def __unicode__(self):
        return '%s [%s]' % (self.title, self.conference)

    @models.permalink
    def get_absolute_url(self):
        return ('conference-talk', (), { 'slug': self.slug })

    def get_event(self):
        return self.event_set.all()[0]

fs_sponsor_logo, _sponsor_logo_path = _build_fs_stuff('sponsor')

class Sponsor(models.Model):
    """
    Attraverso l'elenco di SponsorIncome un'istanza di Sponsor è collegata
    con le informazioni riguardanti tutte le sponsorizzazioni fatte.
    Sempre in SponsorIncome la conferenza è indicata, come in altri posti,
    con una chiave alfanumerica non collegata a nessuna tabella.
    """
    sponsor = models.CharField(max_length = 100, help_text = 'nome dello sponsor')
    slug = models.SlugField()
    url = models.URLField(verify_exists = False, blank = True)
    logo = models.ImageField(
        upload_to = _sponsor_logo_path, blank = True, storage = fs_sponsor_logo,
        help_text = 'Inserire un immagine raster sufficientemente grande da poter essere scalata al bisogno'
    )

    class Meta:
        ordering = ['sponsor']

    def __unicode__(self):
        return self.sponsor

def postSaveSponsorHandler(sender, **kwargs):
    tool = os.path.join(os.path.dirname(conference.__file__), 'utils', 'resize_image.py')
    null = open('/dev/null')
    p = subprocess.Popen(
        [tool, settings.STUFF_DIR],
        close_fds=True, stdin=null, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.communicate()
post_save.connect(postSaveSponsorHandler, sender=Sponsor)

class SponsorIncome(models.Model):
    sponsor = models.ForeignKey(Sponsor)
    conference = models.CharField(max_length = 20)
    income = models.PositiveIntegerField()
    tags = TagField()

    class Meta:
        ordering = ['conference']

fs_mediapartner_logo, _mediapartner_logo_path = _build_fs_stuff('media-partner')

class MediaPartner(models.Model):
    """
    I media partner sono degli sponsor che non pagano ma che offrono visibilità
    di qualche tipo.
    """
    partner = models.CharField(max_length = 100, help_text = 'nome del media partner')
    slug = models.SlugField()
    url = models.URLField(verify_exists = False, blank = True)
    logo = models.ImageField(
        upload_to = _mediapartner_logo_path, blank = True, storage = fs_mediapartner_logo,
        help_text = 'Inserire un immagine raster sufficientemente grande da poter essere scalata al bisogno'
    )

    class Meta:
        ordering = ['partner']

    def __unicode__(self):
        return self.partner

post_save.connect(postSaveSponsorHandler, sender=MediaPartner)

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
            return self.talk.title
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

try:
    assert settings.GOOGLE_MAPS_CONFERENCE['key']
except (AttributeError, KeyError, AssertionError):
    pass
else:
    def postSaveHotelHandler(sender, **kwargs):
        query = sender.objects.exclude(address = '').filter(lng = 0.0).filter(lat = 0.0)
        for obj in query:
            data = conference.gmap.geocode(
                obj.address,
                settings.GOOGLE_MAPS_CONFERENCE['key'],
                settings.GOOGLE_MAPS_CONFERENCE.get('country')
            )
            if data['Status']['code'] == 200:
                point = data['Placemark'][0]['Point']['coordinates']
                lng, lat = point[0:2]
                obj.lng = lng
                obj.lat = lat
                obj.save()
    post_save.connect(postSaveHotelHandler, sender=Hotel)

class DidYouKnow(models.Model):
    """
    Lo sai che?
    """
    visible = models.BooleanField('visible', default = True)
    messages = generic.GenericRelation(MultilingualContent)
