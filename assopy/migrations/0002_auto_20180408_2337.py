# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('conference', '0001_initial'),
        ('assopy', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='vatfare',
            name='fare',
            field=models.ForeignKey(to='conference.Fare'),
        ),
        migrations.AddField(
            model_name='vatfare',
            name='vat',
            field=models.ForeignKey(to='assopy.Vat'),
        ),
        migrations.AddField(
            model_name='vat',
            name='fares',
            field=models.ManyToManyField(to='conference.Fare', null=True, through='assopy.VatFare', blank=True),
        ),
        migrations.AddField(
            model_name='useroauthinfo',
            name='user',
            field=models.ForeignKey(related_name='oauth_infos', to='assopy.User'),
        ),
        migrations.AddField(
            model_name='useridentity',
            name='user',
            field=models.ForeignKey(related_name='identities', to='assopy.User'),
        ),
        migrations.AddField(
            model_name='user',
            name='country',
            field=models.ForeignKey(verbose_name='Country', blank=True, to='assopy.Country', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='user',
            field=models.OneToOneField(related_name='assopy_user', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='token',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='refundorderitem',
            name='orderitem',
            field=models.ForeignKey(to='assopy.OrderItem'),
        ),
        migrations.AddField(
            model_name='refundorderitem',
            name='refund',
            field=models.ForeignKey(to='assopy.Refund'),
        ),
        migrations.AddField(
            model_name='refund',
            name='credit_note',
            field=models.OneToOneField(null=True, blank=True, to='assopy.CreditNote'),
        ),
        migrations.AddField(
            model_name='refund',
            name='invoice',
            field=models.ForeignKey(to='assopy.Invoice', null=True),
        ),
        migrations.AddField(
            model_name='refund',
            name='items',
            field=models.ManyToManyField(to='assopy.OrderItem', through='assopy.RefundOrderItem'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='order',
            field=models.ForeignKey(to='assopy.Order'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='ticket',
            field=models.OneToOneField(null=True, blank=True, to='conference.Ticket'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='vat',
            field=models.ForeignKey(to='assopy.Vat'),
        ),
        migrations.AddField(
            model_name='order',
            name='country',
            field=models.ForeignKey(verbose_name='Country', to='assopy.Country', null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='user',
            field=models.ForeignKey(related_name='orders', to='assopy.User'),
        ),
        migrations.AddField(
            model_name='invoicelog',
            name='invoice',
            field=models.ForeignKey(to='assopy.Invoice', null=True),
        ),
        migrations.AddField(
            model_name='invoicelog',
            name='order',
            field=models.ForeignKey(to='assopy.Order', null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='order',
            field=models.ForeignKey(related_name='invoices', to='assopy.Order'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='vat',
            field=models.ForeignKey(to='assopy.Vat'),
        ),
        migrations.AddField(
            model_name='creditnote',
            name='invoice',
            field=models.ForeignKey(related_name='credit_notes', to='assopy.Invoice'),
        ),
        migrations.AddField(
            model_name='coupon',
            name='conference',
            field=models.ForeignKey(to='conference.Conference'),
        ),
        migrations.AddField(
            model_name='coupon',
            name='fares',
            field=models.ManyToManyField(to='conference.Fare', blank=True),
        ),
        migrations.AddField(
            model_name='coupon',
            name='user',
            field=models.ForeignKey(blank=True, to='assopy.User', null=True),
        ),
        migrations.AlterUniqueTogether(
            name='vatfare',
            unique_together=set([('fare', 'vat')]),
        ),
        migrations.AlterUniqueTogether(
            name='refundorderitem',
            unique_together=set([('orderitem', 'refund')]),
        ),
    ]
