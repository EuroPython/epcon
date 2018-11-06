# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assopy', '0004_add_order_payment_date'),
    ]

    operations = [
        migrations.RenameField(
            model_name='invoice',
            old_name='invoice_copy_full_html',
            new_name='html',
        ),
    ]
