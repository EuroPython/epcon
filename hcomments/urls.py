# -*- coding: utf-8 -*-
from django.conf.urls import url

from hcomments import views


urlpatterns = [
    url(r'post$', views.post_comment, name='hcomments-post-comment',),
]
