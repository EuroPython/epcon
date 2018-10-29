# -*- coding: utf-8 -*-
from django.conf.urls import url

from hcomments import views as hcomments_views


urlpatterns = [
    url(r'post$', hcomments_views.post_comment, name='hcomments-post-comment',),
]
