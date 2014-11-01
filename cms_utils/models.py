# -*- coding: utf-8 -*-
from markitup.fields import MarkupField
from cms.models import CMSPlugin


class MarkitUpPluginModel(CMSPlugin):
    body = MarkupField()