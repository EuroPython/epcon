# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conference', '0002_talk_domain'),
    ]

    operations = [
        migrations.AddField(
            model_name='talk',
            name='domain_level',
            field=models.CharField(default=b'beginner', max_length=12, verbose_name='Audience Domain Level', choices=[(b'beginner', 'Beginner'), (b'intermediate', 'Intermediate'), (b'advanced', 'Advanced')]),
        ),
        migrations.AlterField(
            model_name='talk',
            name='level',
            field=models.CharField(default=b'beginner', max_length=12, verbose_name='Audience Python level', choices=[(b'beginner', 'Beginner'), (b'intermediate', 'Intermediate'), (b'advanced', 'Advanced')]),
        ),
    ]
