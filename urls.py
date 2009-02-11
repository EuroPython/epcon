# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^speakers/(?P<slug>.*)', 'conference.views.speaker'),
)

