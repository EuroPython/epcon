# -*- coding: UTF-8 -*-
from django.core.urlresolvers import reverse
from django.contrib.comments.templatetags import comments as cc

from hcomments import forms
from hcomments import models
from hcomments import settings


def get_model():
    return models.HComment


def get_form(request=None):
    if request and settings.RECAPTCHA(request):
        return forms.HCommentFormWithCaptcha
    else:
        return forms.HCommentForm


def get_form_target():
    return reverse('hcomments-post-comment')


# Monkey patching the default Node of `{% get_comment_form %}` in order to pass request to `get_form`

class CommentFormNode(cc.CommentFormNode):
    def get_form(self, context):
        obj = self.get_object(context)
        if obj and 'request' in context:
            return get_form(context['request'])(obj)
        else:
            return super(CommentFormNode, self).get_form(context)

cc.CommentFormNode = CommentFormNode
