import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("conference", "0008_add_news_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="talk",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="talk",
            name="modified",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name="talk",
            name="uuid",
            field=models.CharField(
                default=uuid.uuid4, max_length=40, unique=False,
            ),
        ),
    ]
