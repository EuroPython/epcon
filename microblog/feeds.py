# -*- coding: UTF-8 -*-
import os.path
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.syndication.feeds import Feed, FeedDoesNotExist
from microblog import models

from tagging.models import Tag

def g(key, value):
    return getattr(settings, key, value)

class LatestPosts(Feed):

    def __init__(self, *args, **kw):
        super(LatestPosts, self).__init__(*args, **kw)
        class D(dict):
            def __getitem__(self, k):
                try:
                    return super(D, self).__getitem__(k)
                except KeyError:
                    raise FeedDoesNotExist()
        self.languages = D((l, l) for l, n in settings.LANGUAGES)
        self.languages[None] = settings.LANGUAGES[0][0]

    def get_object(self, lang_code):
        if not lang_code:
            return None
        elif len(lang_code) > 1:
            raise ObjectDoesNotExist()
        return str(lang_code[0])

    def link(self, obj):
        l = self.languages[obj]
        return os.path.join(g('MICROBLOG_LINK', '/'), l)

    title = g('MICROBLOG_TITLE', 'Microblog feed')
    description = g('MICROBLOG_DESCRIPTION', 'latest post')

    def items(self, obj):
        l = self.languages[obj]
        return models.PostContent.objects.all().filter(language = l).order_by('-post__date')[:10]

    def item_pubdate(self, obj):
        return obj.post.date

    def item_categories(self, obj):
        return ( x.name for x in Tag.objects.get_for_object(obj.post))

    def item_author_name(self, obj):
        user = obj.post.author
        return '%s %s' % (user.first_name, user.last_name)
