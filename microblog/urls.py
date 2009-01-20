# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *
from microblog import views

urlpatterns = patterns('',
    (r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\w{1,2})/(?P<slug>[^/]+)/?$', views.post),
)


