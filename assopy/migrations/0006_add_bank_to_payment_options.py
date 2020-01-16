


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assopy', '0005_simplify_invoice_html_field_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='method',
            field=models.CharField(max_length=6, choices=[(b'cc', b'Credit Card'), (b'paypal', b'PayPal'), (b'bank', b'Bank')]),
        ),
    ]
