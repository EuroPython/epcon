# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-29 14:29
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('django_comments', '0003_add_submit_date_index'),
        ('hcomments', '0003_remove_subscription_models'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='hcomment',
            name='comment_ptr',
        ),
        migrations.DeleteModel(
            name='HComment',
        ),
    ]