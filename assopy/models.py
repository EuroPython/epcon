# -*- coding: UTF-8 -*-
from django.db import models

class User(models.Model):
    user = models.OneToOneField("auth.User", related_name='assopy_user')
    # aggiungere id backend

class UserIdentity(models.Model):
    user = models.ForeignKey(User)
    identifier = models.CharField(max_length=255, primary_key=True)
    provider = models.CharField(max_length=255)
    display_name = models.TextField(blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    birthday = models.DateField(null=True)
    email = models.EmailField(blank=True)
    url = models.URLField(verify_exists=False)
    photo = models.URLField(verify_exists=False)
    phoneNumber = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
