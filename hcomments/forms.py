# -*- coding: utf-8 -*-
from django_comments.forms import CommentForm

from hcomments import models


class HCommentForm(CommentForm):
    def get_comment_model(self):
        return models.HComment

    def get_comment_create_data(self):
        data = super(HCommentForm, self).get_comment_create_data()
        return data
