# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conference', '0005_add_captcha_question'),
    ]

    operations = [
        migrations.AlterField(
            model_name='talk',
            name='abstract_extra',
            field=models.TextField(default=b'', help_text='<p>Please enter instructions for attendees.</p>', verbose_name='Talk abstract extra', blank=True),
        ),
        migrations.AlterField(
            model_name='talk',
            name='domain',
            field=models.CharField(default=b'', max_length=20, blank=True, choices=[(b'business_track', b'Business Track'), (b'devops', b'DevOps'), (b'django', b'Django Track'), (b'education', b'Educational Track'), (b'general', b'General Python'), (b'hw_iot', b'Hardware/IoT Track'), (b'pydata', b'PyData Track'), (b'science', b'Science Track'), (b'web', b'Web Track'), (b'', b'Other')]),
        ),
        migrations.AlterField(
            model_name='talk',
            name='status',
            field=models.CharField(max_length=8, choices=[(b'proposed', 'Proposed'), (b'accepted', 'Accepted'), (b'canceled', 'Canceled'), (b'waitlist', 'Waitlist')]),
        ),
    ]
