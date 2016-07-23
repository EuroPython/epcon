# -*- coding: UTF-8 -*-
import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'deps'))

# è necessario spostare qui (originariamente era in settings.py) la
# registrazione della pingback function perchè register_pingback risolve
# immediatamente il nome passato e la conseguente importazione di
# microblog.view causa un import circolare
import models
import settings

if settings.MICROBLOG_PINGBACK_SERVER:
    from pingback import register_pingback

    if settings.MICROBLOG_URL_STYLE == 'date':
        def _pb_instance(year, month, day, slug):
            return models.PostContent.objects.getBySlugAndDate(slug, year, month, day)
    elif settings.MICROBLOG_URL_STYLE == 'category':
        def _pb_instance(category, slug):
            return models.PostContent.objects.getBySlugAndCategory(slug, category)

    register_pingback('microblog.views.post_detail', _pb_instance)
