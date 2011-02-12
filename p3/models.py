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
    ('omnivorous', 'Omnivorous'),
    ('vegetarian', 'Vegetarian'),
    #('vegan', 'Vegan'),
    #('kosher', 'Kosher'),
)
ATTENDEE_EXPERIENCES = (
    (0, '0'),
    (1, '1'),
    (2, '2'),
    (3, '3'),
    (4, '4'),
    (5, '5'),
)
class AttendeeProfile(models.Model):
    attendee = models.OneToOneField('conference.attendee', related_name='p3_conference')
    shirt_size = models.CharField(max_length=2, choices=ATTENDEE_SHIRT_SIZES, default='l')
    python_experience = models.PositiveIntegerField(choices=ATTENDEE_EXPERIENCES, default=0)
    diet = models.CharField(max_length=10, choices=ATTENDEE_DIETS, default='omnivorous')
    tagline = models.CharField(max_length=60, blank=True, help_text='a (funny?) tagline for the attendee')

