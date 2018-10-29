# -*- coding: utf-8 -*-
from django import forms
from django_comments.forms import CommentForm

from hcomments import models


class HCommentForm(CommentForm):
    parent = forms.IntegerField(
        min_value=0, required=False, initial=0,
        widget=forms.HiddenInput,
    )

    def get_comment_model(self):
        return models.HComment

    def get_comment_create_data(self):
        data = super(HCommentForm, self).get_comment_create_data()
        if self.cleaned_data['parent'] == 0:
            data['parent'] = None
        else:
            data['parent'] = models.HComment.objects.get(id=self.cleaned_data['parent'])
        return data
