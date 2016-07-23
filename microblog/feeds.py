# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.contrib.syndication.views import Feed, FeedDoesNotExist
from django.core.urlresolvers import reverse

from microblog import models
from microblog import settings

import os.path

class FeedsDict(dict):
    """
    dict custom che solleva un FeedDoesNotExist al posto di un KeyError
    """
    def __getitem__(self, k):
        try:
            return super(FeedsDict, self).__getitem__(k)
        except KeyError:
            raise FeedDoesNotExist()

languages = FeedsDict((l, l) for l, n in dsettings.LANGUAGES)
languages[None] = settings.MICROBLOG_DEFAULT_LANGUAGE

class LatestPosts(Feed):

    def get_object(self, request, lang_code=None):
        return languages[lang_code]

    def link(self, obj):
        try:
            path = reverse('microblog-feeds-latest')
        except:
            path = reverse('microblog-feeds-latest', kwargs={'lang_code': obj})
        return os.path.join(dsettings.DEFAULT_URL_PREFIX, path)

    title = settings.MICROBLOG_TITLE
    description = settings.MICROBLOG_DESCRIPTION
    description_template = 'microblog/feeds/item_description.html'
    author_name = settings.MICROBLOG_AUTHOR_NAME
    author_email = settings.MICROBLOG_AUTHOR_EMAIL
    author_link = settings.MICROBLOG_AUTHOR_LINK

    def items(self, obj):
        return models.PostContent.objects\
                .all()\
                .filter(language=obj, post__status='P')\
                .exclude(headline='')\
                .select_related('post', 'post__author')\
                .order_by('-post__date')[:10]

    def item_title(self, item):
        return item.headline

    def item_description(self, item):
        return item.body

    def item_pubdate(self, item):
        return item.post.date

    def item_categories(self, item):
        return [ x.name for x in item.post.tags.all()]

    def item_author_name(self, item):
        user = item.post.author
        return '%s %s' % (user.first_name, user.last_name)
