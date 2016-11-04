from haystack.indexes import *
from haystack import site

from microblog.models import PostContent
from django.conf import settings

"""
Indicizzo tutti i postcontent nelle varie lingue
successivamente nel template filtrero in base 
al linguaggio i risultati
"""

class PostIndex(SearchIndex):
    text = CharField(document=True, use_template=True)
    title = CharField(model_attr='headline')
    url = CharField(model_attr='get_absolute_url')
    publication_date = DateTimeField(model_attr='post__date')
    language = CharField(model_attr='language')

    def index_queryset(self):
        return PostContent.objects.published().exclude(headline='')

class RealTimePostIndex(RealTimeSearchIndex):
    text = CharField(document=True, use_template=True)
    title = CharField(model_attr='headline')
    url = CharField(model_attr='get_absolute_url')
    publication_date = DateTimeField(model_attr='post__date')
    language = CharField(model_attr='language')

    def get_queryset(self):
        return PostContent.objects.published().exclude(headline='')

if getattr(settings, 'MICROBLOG_HAYSTACK_SEARCH', None):
    if getattr(settings, 'MICROBLOG_REAL_TIME_SEARCH', None):
        site.register(PostContent, RealTimePostIndex)
    else:
        site.register(PostContent, PostIndex)
