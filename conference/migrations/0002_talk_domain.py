


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conference', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='talk',
            name='domain',
            field=models.CharField(default=b'', max_length=20, choices=[(b'business_track', b'Business Track'), (b'devops', b'DevOps'), (b'django', b'Django Track'), (b'education', b'Educational Track'), (b'general', b'General Python'), (b'hw_iot', b'Hardware/IoT Track'), (b'pydata', b'PyData Track'), (b'science', b'Science Track'), (b'web', b'Web Track'), (b'', b'None of the above')]),
        ),
    ]
