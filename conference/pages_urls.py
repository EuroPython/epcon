# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from conference.pages_patch import details

urlpatterns = patterns('',
    # Public pages
    url(r'^$', details, name='pages-root'),
)

urlpatterns += patterns('',
    url(r'^.*?/?(?P<slug>[-\w]+)/$', details, name='pages-details-by-slug'),
)
