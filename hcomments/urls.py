# -*- coding: UTF-8 -*-
from django.conf.urls import *
from microblog import views, models, feeds, settings

urlpatterns = patterns('',
    url(r'post$', 'hcomments.views.post_comment', name='hcomments-post-comment',),
    url(r'delete$', 'hcomments.views.delete_comment', name='hcomments-delete-comment',),
    url(r'private-comment/(?P<cid>\d+)$', 'hcomments.views.moderate_comment', name='hcomments-privaye-comment',),
    url(r'public-comment/(?P<cid>\d+)$', 'hcomments.views.moderate_comment', kwargs={ 'public': True }, name='hcomments-public-comment',),
    url(r'subscribe/$', 'hcomments.views.subscribe', name='hcomments-subscribe',),
)
