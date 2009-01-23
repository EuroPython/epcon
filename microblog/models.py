# -*- coding: UTF-8 -*-
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
import tagging
import tagging.fields

POST_STATUS = (('P', 'Pubblicato'), ('D', 'Bozza'))

class PostManager(models.Manager):
    def published(self):
        return self.all().filter(status = 'P').order_by('-date')

class Post(models.Model):
    date = models.DateTimeField(db_index=True)
    author = models.ForeignKey(User)
    status = models.CharField(max_length = 1, default = 'P', choices = POST_STATUS)
    allow_comments = models.BooleanField()
    tags = tagging.fields.TagField()

    objects = PostManager()

    def __unicode__(self):
        return "Post of %s on %s" % (self.author, self.date)

    class Meta:
        ordering = ('-date',)
        get_latest_by = 'date'

    def is_published(self):
        return self.status == 'P'

    def content(self, lang, fallback=True):
        """
        Ritorna il PostContent nella lingua specificata.
        Se il PostContent non esiste e fallback è False viene sollevata
        l'eccezione ObjectDoesNotExist. Se fallback è True viene prima
        ricercato il PostContent nella lingua di default del sito, se non
        esiste viene ritornato il primo PostContent esistente, se non esiste
        neanche questo viene sollevata l'eccezione ObjectDoesNotExist.
        """
        contents = dict((c.language, c) for c in self.postcontent_set.exclude(headline=''))
        if not contents:
            raise PostContent.DoesNotExist()
        try:
            return contents[lang]
        except KeyError:
            if not fallback:
                raise PostContent.DoesNotExist()

        try:
            return contents[settings.LANGUAGES[0][0]]
        except KeyError:
            return contents.values()[0]

class PostContent(models.Model):
    post = models.ForeignKey(Post)
    language = models.CharField(max_length = 3)
    headline = models.CharField(max_length = 200)
    slug = models.SlugField(unique_for_date = 'post.date')
    summary = models.TextField()
    body = models.TextField()

    @models.permalink
    def get_absolute_url(self):
        date = self.post.date
        return ('microblog-post-detail', (), {
            'year': str(date.year),
            'month': str(date.month).zfill(2),
            'day': str(date.day).zfill(2),
            'slug': self.slug
        })

