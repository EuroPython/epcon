# -*- coding: utf-8 -*-
from django_comments.models import Comment


class HComment(Comment):
    class Meta:
        app_label = 'hcomments'
