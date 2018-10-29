# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.apps import AppConfig
from django.db.models.signals import post_save

import mptt

from hcomments import settings


class HCommentsConfig(AppConfig):
    name = 'hcomments'
    verbose_name = "HComments"

    def ready(self):
        from django_comments.models import Comment
        from django_comments.templatetags import comments as cc

        from hcomments import models
        from hcomments.apps import send_email_to_subscribers


        post_save.connect(send_email_to_subscribers, sender=Comment)
        post_save.connect(send_email_to_subscribers, sender=models.HComment)

        mptt.register(models.HComment)

        # Monkey patching the default Node of `{% get_comment_form %}` in order to pass request to `get_form`
        class CommentFormNode(cc.CommentFormNode):
            def get_form(self, context):
                obj = self.get_object(context)
                if obj and 'request' in context:
                    return get_form(context['request'])(obj)
                else:
                    return super(CommentFormNode, self).get_form(context)

        cc.CommentFormNode = CommentFormNode


def get_model():
    from hcomments import models
    return models.HComment


def get_form(request=None):
    from hcomments import forms
    return forms.HCommentForm


def get_form_target():
    return reverse('hcomments-post-comment')
