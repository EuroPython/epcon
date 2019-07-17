# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2019-07-13 10:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('p3', '0003_add_name_field_to_ticket_conference'),
    ]

    operations = [
        migrations.AlterField(
            model_name='p3profile',
            name='country',
            field=models.CharField(blank=True, db_index=True, default='', max_length=2),
        ),
        migrations.AlterField(
            model_name='p3talk',
            name='sub_community',
            field=models.CharField(choices=[('', 'All'), ('pydata', 'PyData')], default='', max_length=20),
        ),
        migrations.AlterField(
            model_name='ticketconference',
            name='assigned_to',
            field=models.EmailField(blank=True, help_text='Email of the attendee for whom this ticket was bought.', max_length=254),
        ),
        migrations.AlterField(
            model_name='ticketconference',
            name='badge_image',
            field=models.ImageField(blank=True, help_text="A custom badge image instead of the python logo.Don't use a very large image, 250x250 should be fine.", null=True, upload_to='p3/tickets/badge_image'),
        ),
        migrations.AlterField(
            model_name='ticketconference',
            name='diet',
            field=models.CharField(choices=[('omnivorous', 'Omnivorous'), ('vegetarian', 'Vegetarian'), ('other', 'Other')], default='omnivorous', max_length=10),
        ),
        migrations.AlterField(
            model_name='ticketconference',
            name='name',
            field=models.CharField(blank=True, help_text='What name should appear on the badge?', max_length=255),
        ),
        migrations.AlterField(
            model_name='ticketconference',
            name='python_experience',
            field=models.PositiveIntegerField(choices=[(0, 'no comment'), (1, '1 star  (just starting)'), (2, '2 stars (beginner)'), (3, '3 stars (intermediate)'), (4, '4 stars (expert))'), (5, '5 stars (guru level)')], default=0, null=True),
        ),
        migrations.AlterField(
            model_name='ticketconference',
            name='shirt_size',
            field=models.CharField(choices=[('fs', 'S (female)'), ('fm', 'M (female)'), ('fl', 'L (female)'), ('fxl', 'XL (female)'), ('fxxl', 'XXL (female)'), ('fxxxl', '3XL (female)'), ('s', 'S (male)'), ('m', 'M (male)'), ('l', 'L (male)'), ('xl', 'XL (male)'), ('xxl', 'XXL (male)'), ('xxxl', '3XL (male)'), ('xxxxl', '4XL (male)')], default='l', max_length=5),
        ),
    ]
