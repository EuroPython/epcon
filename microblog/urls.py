# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *
from microblog import views, models

urlpatterns = patterns('',
    (
        r'^$', 'django.views.generic.list_detail.object_list',
        {
            'queryset': models.Post.objects.all()
        }
    ),
    (r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\w{1,2})/(?P<slug>[^/]+)/?$', views.post),
)


