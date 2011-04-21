# -*- coding: UTF-8 -*-
from haystack import indexes
from haystack import site
from conference import models

class TalkIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)

site.register(models.Talk, TalkIndex)
