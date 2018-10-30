# -*- coding: utf-8 -*-
from django.conf.urls import url

from hcomments import views as hcomments_views


urlpatterns = [
    url(r'post$', hcomments_views.post_comment, name='hcomments-post-comment',),
    url(r'delete$', hcomments_views.delete_comment, name='hcomments-delete-comment',),
    url(r'private-comment/(?P<cid>\d+)$', hcomments_views.moderate_comment, name='hcomments-privaye-comment',),
    url(r'public-comment/(?P<cid>\d+)$', hcomments_views.moderate_comment, kwargs={ 'public': True }, name='hcomments-public-comment',),
    url(r'subscribe/$', hcomments_views.subscribe, name='hcomments-subscribe',),
]
