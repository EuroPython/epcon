


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assopy', '0003_add_exrate_fields_to_invoice_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_date',
            field=models.DateTimeField(help_text=b'Auto filled by the payments backend', null=True, blank=True),
        ),
    ]
