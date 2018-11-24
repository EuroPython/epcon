# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.apps import AppConfig


class HCommentsConfig(AppConfig):
    name = 'hcomments'
    verbose_name = "HComments"


def get_form_target():
    return reverse('hcomments-post-comment')
