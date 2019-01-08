


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assopy', '0006_add_bank_to_payment_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='customer',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
