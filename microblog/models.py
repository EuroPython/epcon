# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.contrib.auth.models import User
from django.core import mail
from django.db import models
from django.db.models.query import QuerySet
from django.template import Template, Context
from django.utils.importlib import import_module

from taggit.managers import TaggableManager

from microblog import settings
from microblog.django_urls import UrlMixin

import logging

log = logging.getLogger('microblog')

class Category(models.Model):
    name = models.CharField(max_length = 100)
    description = models.TextField(blank = True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __unicode__(self):
        return self.name

POST_STATUS = (('P', 'Pubblicato'), ('D', 'Bozza'))

class PostManager(models.Manager):
    def get_queryset(self):
        return self._QuerySet(self.model)

    def __getattr__(self, name):
        return getattr(self.all(), name)

    class _QuerySet(QuerySet):
        def byLanguage(self, lang):
            return self\
                .filter(postcontent__language=lang)\
                .exclude(id__in=Post.objects.filter(postcontent__language=lang, postcontent__headline=''))

        def byFeatured(self, featured):
            return self.filter(featured=featured)

        def published(self):
            return self.filter(status='P')

class Post(models.Model, UrlMixin):
    date = models.DateTimeField(db_index=True)
    author = models.ForeignKey(User)
    status = models.CharField(max_length = 1, default = 'D', choices = POST_STATUS)
    allow_comments = models.BooleanField()
    category = models.ForeignKey(Category)
    featured = models.BooleanField(default=False)
    image = models.URLField(null=True, blank=True)

    tags = TaggableManager()

    objects = PostManager()

    def __unicode__(self):
        return "Post of %s on %s" % (self.author, self.date)

    class Meta:
        get_latest_by = 'date'

    def is_published(self):
        return self.status == 'P'

    def content(self, lang, fallback=True):
        """
        Ritorna il PostContent nella lingua specificata.
        Se il PostContent non esiste e fallback è False viene sollevata
        l'eccezione ObjectDoesNotExist. Se fallback è True viene prima
        ricercato il PostContent nella lingua di default del blog, poi in
        quella del sito, se non esiste viene ritornato il primo PostContent
        esistente, se non esiste neanche questo viene sollevata l'eccezione
        ObjectDoesNotExist.
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
            c = contents[settings.MICROBLOG_DEFAULT_LANGUAGE]
            c = contents[dsettings.LANGUAGES[0][0]]
        except KeyError:
            c = contents.values()[0]
        return c

    def get_trackback_url(self):
        return self.get_absolute_url() + '/trackback'

    def get_absolute_url(self):
        """
        Non ha molto senso ritornare la url di un Post dato che l'utente
        visualizza i PostContent; ma è molto comodo (per il programmatore)
        avere avere una url che identifica un post senza dover per forza
        passare da una traduzione.
        """
        from dataaccess import post_data
        # utilizzo dataaccess per evitare di fare una query ogni volta solo per
        # recuperare il postcontent e chiedere a lui la url
        data = post_data(self.id, settings.MICROBLOG_DEFAULT_LANGUAGE)
        return data['url']

    get_url_path = get_absolute_url

    def spammed(self, method, value):
        return self.spam_set.filter(method=method, value=value).count() > 0

SPAM_METHODS = (
    ('e', 'email'),
    ('t', 'twitter'),
)
class Spam(models.Model):
    """
    tiene traccia di dove, come e quando un determinato post è stato
    pubblicizzato.
    """
    post = models.ForeignKey(Post)
    method = models.CharField(max_length=1, choices=SPAM_METHODS)
    value = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '%s -> %s' % (self.method, self.value)

class PostContentManager(models.Manager):
    def get_queryset(self):
        return self._QuerySet(self.model)

    def __getattr__(self, name):
        return getattr(self.all(), name)

    class _QuerySet(QuerySet):
        def getBySlugAndDate(self, slug, year, month, day):
            return self.get(
                slug = slug,
                post__date__year = int(year),
                post__date__month = int(month),
                post__date__day = int(day),
            )

        def getBySlugAndCategory(self, slug, category):
            return self.get(
                slug = slug,
                post__category__name = category,
            )

        def published(self, language=None):
            q = self\
                .filter(post__status='P')\
                .order_by('-post__date')
            if language:
                q = q.filter(language=language)
            return q

class PostContent(models.Model, UrlMixin):
    post = models.ForeignKey(Post)
    language = models.CharField(max_length = 3)
    headline = models.CharField(max_length = 200)
    slug = models.SlugField(unique_for_date = 'post.date')
    summary = models.TextField()
    body = models.TextField()

    objects = PostContentManager()

    @classmethod
    def build_absolute_url(cls, post, content):
        if settings.MICROBLOG_URL_STYLE == 'date':
            date = post.date
            return ('microblog-post-detail', (), {
                'year': str(date.year),
                'month': str(date.month).zfill(2),
                'day': str(date.day).zfill(2),
                'slug': content.slug
            })
        elif settings.MICROBLOG_URL_STYLE == 'category':
            return ('microblog-post-detail', (), {
                'category': post.category.name,
                'slug': content.slug
            })

    @models.permalink
    def get_absolute_url(self):
        # è molto brutto che una cosa apparantemente innocua come la
        # costruzione della url richieda una query verso il db; per minimizzare
        # gli effetti faccio cache a livello di istanza
        if not hasattr(self, '_url'):
            self._url = PostContent.build_absolute_url(self.post, self)
        return self._url

    get_url_path = get_absolute_url

    def new_trackback(self, url, blog_name='', title='', excerpt=''):
        tb = Trackback()
        tb.content = self
        tb.url = url
        tb.blog_name = blog_name
        tb.title = title
        tb.excerpt = excerpt
        tb.save()
        return tb

class Trackback(models.Model):
    content = models.ForeignKey(PostContent)
    type = models.CharField(max_length = 2, default = 'tb')
    date = models.DateTimeField(auto_now_add = True)
    url = models.CharField(max_length = 1000)
    blog_name = models.TextField()
    title = models.TextField()
    excerpt = models.TextField()

    class Meta:
        ordering = ['-date']

