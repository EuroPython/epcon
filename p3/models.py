# -*- coding: UTF-8 -*-
from django.db import models

ATTENDEE_SHIRT_SIZES = (
    ('s', 'S'),
    ('m', 'M'),
    ('l', 'L'),
    ('xl', 'XL'),
    ('xxl', 'XXL'),
)
ATTENDEE_DIETS = (
    ('omnivorous', 'Vegetarian'),
    ('vegetarian', 'Vegetarian'),
    #('vegan', 'Vegan'),
    #('kosher', 'Kosher'),
)
class AttendeeProfile(models.Model):
    attendee = models.OneToOneField('conference.attendee', related_name='p3_conference')
    shirt_size = models.CharField(max_length=2, choices=ATTENDEE_SHIRT_SIZES)
    python_experience = models.PositiveIntegerField(default=0)
    diet = models.CharField(max_length=10, choices=ATTENDEE_DIETS)
    tagline = models.CharField(max_length=60, blank=True, help_text='a (funny?) tagline for the attendee')

