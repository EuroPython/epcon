# -*- coding: UTF-8 -*-
from haystack import indexes
from haystack import site
from conference import models

class EventIndex(indexes.SearchIndex):
    text = indexes.CharField(document=True, use_template=True)
    conference = indexes.CharField(model_attr='schedule__conference')

    def get_queryset(self):
        return models.Event.objects.all()

site.register(models.Event, EventIndex)
