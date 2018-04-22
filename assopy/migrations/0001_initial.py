# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import common.django_urls


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('iso', models.CharField(max_length=2, serialize=False, verbose_name='ISO alpha-2', primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('vat_company', models.BooleanField(default=False, verbose_name=b'VAT for company')),
                ('vat_company_verify', models.CharField(default=b'-', max_length=1, choices=[(b'-', b'None'), (b'v', b'VIES')])),
                ('vat_person', models.BooleanField(default=False, verbose_name=b'VAT for person')),
                ('iso3', models.CharField(max_length=3, null=True, verbose_name='ISO alpha-3')),
                ('numcode', models.PositiveSmallIntegerField(null=True, verbose_name='ISO numeric')),
                ('printable_name', models.CharField(max_length=128, verbose_name='Country name')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name_plural': 'Countries',
            },
        ),
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=10)),
                ('start_validity', models.DateField(null=True, blank=True)),
                ('end_validity', models.DateField(null=True, blank=True)),
                ('max_usage', models.PositiveIntegerField(default=0, help_text=b'numero di volte che questo coupon pu\xc3\xb2 essere usato')),
                ('items_per_usage', models.PositiveIntegerField(default=0, help_text=b"numero di righe d'ordine su cui questo coupon ha effetto")),
                ('description', models.CharField(max_length=100, blank=True)),
                ('value', models.CharField(help_text=b'importo, eg: 10, 15%, 8.5', max_length=8)),
            ],
        ),
        migrations.CreateModel(
            name='CreditNote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(unique=True, max_length=20)),
                ('assopy_id', models.CharField(max_length=22, null=True)),
                ('emit_date', models.DateField()),
                ('price', models.DecimalField(max_digits=6, decimal_places=2)),
            ],
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=20, unique=True, null=True)),
                ('assopy_id', models.CharField(max_length=22, unique=True, null=True, blank=True)),
                ('emit_date', models.DateField()),
                ('payment_date', models.DateField(null=True, blank=True)),
                ('price', models.DecimalField(max_digits=6, decimal_places=2)),
                ('issuer', models.TextField()),
                ('invoice_copy_full_html', models.TextField()),
                ('note', models.TextField(help_text=b"Testo libero da riportare in fattura; posto al termine delle righe d'ordine riporta di solito gli estremi di legge", blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(unique=True, max_length=20)),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=20, null=True)),
                ('assopy_id', models.CharField(max_length=22, unique=True, null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('method', models.CharField(max_length=6, choices=[(b'cc', b'Credit Card'), (b'paypal', b'PayPal')])),
                ('payment_url', models.TextField(blank=True)),
                ('_complete', models.BooleanField(default=False)),
                ('billing_notes', models.TextField(blank=True)),
                ('card_name', models.CharField(max_length=200, verbose_name='Card name')),
                ('vat_number', models.CharField(max_length=22, verbose_name='Vat Number', blank=True)),
                ('cf_code', models.CharField(max_length=16, verbose_name='Fiscal Code', blank=True)),
                ('address', models.CharField(max_length=150, verbose_name='Address', blank=True)),
                ('stripe_charge_id', models.CharField(max_length=64, unique=True, null=True, verbose_name='Charge Stripe ID')),
            ],
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=10)),
                ('price', models.DecimalField(max_digits=6, decimal_places=2)),
                ('description', models.CharField(max_length=100, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Refund',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('done', models.DateTimeField(null=True)),
                ('status', models.CharField(default=b'pending', max_length=8, choices=[(b'pending', b'Pending'), (b'approved', b'Approved'), (b'rejected', b'Rejected'), (b'refunded', b'Refunded')])),
                ('reason', models.CharField(max_length=200, blank=True)),
                ('internal_note', models.TextField(help_text=b'For internal use (not shown to the user)', blank=True)),
                ('reject_reason', models.TextField(help_text=b'Included in the email sent to the user', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='RefundOrderItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='Token',
            fields=[
                ('token', models.CharField(max_length=36, serialize=False, primary_key=True)),
                ('ctype', models.CharField(max_length=1)),
                ('payload', models.TextField(blank=b'')),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            bases=(models.Model, common.django_urls.UrlMixin),
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('token', models.CharField(max_length=36, unique=True, null=True, blank=True)),
                ('assopy_id', models.CharField(max_length=22, unique=True, null=True)),
                ('card_name', models.CharField(help_text='The name used for orders and invoices', max_length=200, verbose_name='Card name', blank=True)),
                ('vat_number', models.CharField(help_text='Your VAT number if applicable', max_length=22, verbose_name='Vat Number', blank=True)),
                ('cf_code', models.CharField(help_text='Needed only for Italian customers', max_length=16, verbose_name='Fiscal Code', blank=True)),
                ('address', models.CharField(help_text='Insert the full address, including city and zip code. We will help you through google.', max_length=150, verbose_name='Address and City', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserIdentity',
            fields=[
                ('identifier', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('provider', models.CharField(max_length=255)),
                ('display_name', models.TextField(blank=True)),
                ('gender', models.CharField(max_length=10, blank=True)),
                ('birthday', models.DateField(null=True)),
                ('email', models.EmailField(max_length=254, blank=True)),
                ('url', models.URLField()),
                ('photo', models.URLField()),
                ('phoneNumber', models.CharField(max_length=20, blank=True)),
                ('address', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserOAuthInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('service', models.CharField(max_length=20)),
                ('token', models.CharField(max_length=200)),
                ('secret', models.CharField(max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name='Vat',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.DecimalField(max_digits=2, decimal_places=0)),
                ('description', models.CharField(max_length=125, null=True, blank=True)),
                ('invoice_notice', models.TextField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='VatFare',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
    ]
