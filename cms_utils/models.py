from cms.models import CMSPlugin
from django.db import models
from markitup.fields import MarkupField


class MarkitUpPluginModel(CMSPlugin):
    body = MarkupField()


class TemplatePluginModel(CMSPlugin):
    body = models.TextField()
