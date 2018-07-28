# -*- coding: UTF-8 -*-
from django.db import models
from django.contrib.auth.models import User
from django_comments.models import Comment
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from mptt.managers import TreeManager
from mptt.models import MPTTModel


class HComment(MPTTModel, Comment):
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')
    tree = TreeManager()


class ThreadSubscriptionManager(models.Manager):
    def unsubscribe(self, object, user):
        if self.subscribed(object, user):
            ct = ContentType.objects.get_for_model(object)
            ThreadSubscription.objects.get(content_type=ct, object_id=object.pk, user=user).delete()

    def subscribe(self, object, user):
        if not self.subscribed(object, user):
            ThreadSubscription(content_object=object, user=user).save()

    def subscribed(self, object, user):
        ct = ContentType.objects.get_for_model(object)
        return self.filter(content_type=ct, object_id=object.pk, user=user).exists()

    def subscriptions(self, object):
        ct = ContentType.objects.get_for_model(object)
        return User.objects.filter(id__in=self.filter(content_type=ct, object_id=object.pk).values('user'))

class ThreadSubscription(models.Model):
    user = models.ForeignKey('auth.user')
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    objects = ThreadSubscriptionManager()

    class Meta:
        unique_together = ('user', 'object_id', 'content_type')
