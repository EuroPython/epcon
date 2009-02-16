# -*- coding: UTF-8 -*-
import datetime
import os.path
from django.conf import settings
from django.db import models

import tagging
from tagging.fields import TagField

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
fs_speaker = FileSystemStorage(
    location = os.path.join(settings.STUFF_DIR, 'speaker'),
    base_url = urlparse.urljoin(settings.MEDIA_URL, 'stuff/speaker/')
)

def _speaker_image_path(instance, filename):
    return instance.slug + os.path.splitext(filename)[1].lower()

class Speaker(models.Model):
    nome = models.CharField('nome e cognome speaker', max_length = 100)
    slug = models.SlugField()
    homepage = models.URLField(verify_exists = False, blank = True)
    attivita = models.CharField(max_length = 50, blank = True)
    settore = models.CharField(max_length = 50, blank = True)
    provenienza = models.CharField(max_length = 100, blank = True)
    immagine = models.ImageField(upload_to = _speaker_image_path, blank = True, storage = fs_speaker)
    bios = generic.GenericRelation(MultilingualContent)

    class Meta:
        ordering = ['nome']

    def __unicode__(self):
        return self.nome

    @models.permalink
    def get_absolute_url(self):
        return ('conference-speaker', (), { 'slug': self.slug })

TALK_DURATION = (
    (30, '30 minuti'),
    (45, '45 minuti'),
    (60, '60 minuti'),
    (90, '90 minuti'),
)
TALK_LANGUAGES = (
    ('it', 'Italiano'),
    ('en', 'Inglese'),
)

fs_slides = FileSystemStorage(
    location = os.path.join(settings.STUFF_DIR, 'slides'),
    base_url = urlparse.urljoin(settings.MEDIA_URL, 'stuff/slides/')
)

def _talk_slides_path(instance, filename):
    return instance.slug + os.path.splitext(filename)[1].lower()

class Talk(models.Model):
    titolo = models.CharField('titolo del talk', max_length = 100)
    slug = models.SlugField()
    speaker = models.ForeignKey(Speaker)
    durata = models.IntegerField(choices = TALK_DURATION)
    lingua = models.CharField('lingua del talk', max_length = 3, choices = TALK_LANGUAGES)
    abstracts = generic.GenericRelation(MultilingualContent)
    slides = models.FileField(upload_to = _talk_slides_path, blank = True, storage = fs_slides)
    video = models.URLField(verify_exists = False, blank = True)

    def __unicode__(self):
        return self.titolo

    @models.permalink
    def get_absolute_url(self):
        return ('conference-talk', (), { 'slug': self.slug })

fs_logo = FileSystemStorage(
    location = os.path.join(settings.STUFF_DIR, 'sponsor'),
    base_url = urlparse.urljoin(settings.MEDIA_URL, 'stuff/sponsor/')
)

def _sponsor_logo_path(instance, filename):
    return instance.slug + os.path.splitext(filename)[1].lower()

class Sponsor(models.Model):
    """

    """
    sponsor = models.CharField(max_length = 100, help_text = 'nome dello sponsor')
    slug = models.SlugField()
    url = models.URLField(verify_exists = False, blank = True)
    logo = models.ImageField(
        upload_to = _sponsor_logo_path, blank = True, storage = fs_logo,
        help_text = 'Inserire un immagine raster sufficientemente grande da poter essere scalata al bisogno'
    )
    conferenze = TagField()
    tags = TagField()

    def __unicode__(self):
        return self.sponsor


class Schedule(models.Model):
    conferenza = models.CharField(help_text = 'nome della conferenza', max_length = 50)
    data = models.DateField()

class Track(models.Model):
    schedule = models.ForeignKey(Schedule)
    track = models.CharField('nome track', max_length = 20)
    titolo = models.TextField('titolo della track', help_text = 'HTML supportato')

    def __unicode__(self):
        return self.track

class Event(models.Model):
    """
    """
    schedule = models.ForeignKey(Schedule)
    talk = models.ForeignKey(Talk, blank = True)
    custom = models.TextField(blank = True)
    ora_inizio = models.TimeField()
    track = TagField(help_text = 'Inserire uno o più nomi di track, oppure "keynote"')
    sponsor = models.ForeignKey(Sponsor, blank = True)

    def __unicode__(self):
        if self.talk:
            return self.talk
        else:
            return self.custom
