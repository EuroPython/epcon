# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Country'
        db.create_table(u'assopy_country', (
            ('iso', self.gf('django.db.models.fields.CharField')(max_length=2, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('vat_company', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('vat_company_verify', self.gf('django.db.models.fields.CharField')(default='-', max_length=1)),
            ('vat_person', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('iso3', self.gf('django.db.models.fields.CharField')(max_length=3, null=True)),
            ('numcode', self.gf('django.db.models.fields.PositiveSmallIntegerField')(null=True)),
            ('printable_name', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal(u'assopy', ['Country'])

        # Adding model 'Token'
        db.create_table(u'assopy_token', (
            ('token', self.gf('django.db.models.fields.CharField')(max_length=36, primary_key=True)),
            ('ctype', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('payload', self.gf('django.db.models.fields.TextField')(blank='')),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'assopy', ['Token'])

        # Adding model 'User'
        db.create_table(u'assopy_user', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='assopy_user', unique=True, to=orm['auth.User'])),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=36, unique=True, null=True, blank=True)),
            ('assopy_id', self.gf('django.db.models.fields.CharField')(max_length=22, unique=True, null=True)),
            ('card_name', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('vat_number', self.gf('django.db.models.fields.CharField')(max_length=22, blank=True)),
            ('cf_code', self.gf('django.db.models.fields.CharField')(max_length=16, blank=True)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.Country'], null=True, blank=True)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=150, blank=True)),
        ))
        db.send_create_signal(u'assopy', ['User'])

        # Adding model 'UserIdentity'
        db.create_table(u'assopy_useridentity', (
            ('identifier', self.gf('django.db.models.fields.CharField')(max_length=255, primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='identities', to=orm['assopy.User'])),
            ('provider', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('display_name', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('gender', self.gf('django.db.models.fields.CharField')(max_length=10, blank=True)),
            ('birthday', self.gf('django.db.models.fields.DateField')(null=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('photo', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('phoneNumber', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
            ('address', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'assopy', ['UserIdentity'])

        # Adding model 'UserOAuthInfo'
        db.create_table(u'assopy_useroauthinfo', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='oauth_infos', to=orm['assopy.User'])),
            ('service', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('secret', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal(u'assopy', ['UserOAuthInfo'])

        # Adding model 'Coupon'
        db.create_table(u'assopy_coupon', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('conference', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Conference'])),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('start_validity', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('end_validity', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('max_usage', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('items_per_usage', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.User'], null=True, blank=True)),
        ))
        db.send_create_signal(u'assopy', ['Coupon'])

        # Adding M2M table for field fares on 'Coupon'
        m2m_table_name = db.shorten_name(u'assopy_coupon_fares')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('coupon', models.ForeignKey(orm[u'assopy.coupon'], null=False)),
            ('fare', models.ForeignKey(orm[u'conference.fare'], null=False))
        ))
        db.create_unique(m2m_table_name, ['coupon_id', 'fare_id'])

        # Adding model 'Vat'
        db.create_table(u'assopy_vat', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('value', self.gf('django.db.models.fields.DecimalField')(max_digits=2, decimal_places=0)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=125, null=True, blank=True)),
            ('invoice_notice', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'assopy', ['Vat'])

        # Adding model 'VatFare'
        db.create_table(u'assopy_vatfare', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('fare', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Fare'])),
            ('vat', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.Vat'])),
        ))
        db.send_create_signal(u'assopy', ['VatFare'])

        # Adding unique constraint on 'VatFare', fields ['fare', 'vat']
        db.create_unique(u'assopy_vatfare', ['fare_id', 'vat_id'])

        # Adding model 'Order'
        db.create_table(u'assopy_order', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=20, null=True)),
            ('assopy_id', self.gf('django.db.models.fields.CharField')(max_length=22, unique=True, null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='orders', to=orm['assopy.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('method', self.gf('django.db.models.fields.CharField')(max_length=6)),
            ('payment_url', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('_complete', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('billing_notes', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('card_name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('vat_number', self.gf('django.db.models.fields.CharField')(max_length=22, blank=True)),
            ('cf_code', self.gf('django.db.models.fields.CharField')(max_length=16, blank=True)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.Country'], null=True)),
            ('address', self.gf('django.db.models.fields.CharField')(max_length=150, blank=True)),
        ))
        db.send_create_signal(u'assopy', ['Order'])

        # Adding model 'OrderItem'
        db.create_table(u'assopy_orderitem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.Order'])),
            ('ticket', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['conference.Ticket'], unique=True, null=True, blank=True)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=6, decimal_places=2)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('vat', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.Vat'])),
        ))
        db.send_create_signal(u'assopy', ['OrderItem'])

        # Adding model 'InvoiceLog'
        db.create_table(u'assopy_invoicelog', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('order', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.Order'], null=True)),
            ('invoice', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.Invoice'], null=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'assopy', ['InvoiceLog'])

        # Adding model 'Invoice'
        db.create_table(u'assopy_invoice', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order', self.gf('django.db.models.fields.related.ForeignKey')(related_name='invoices', to=orm['assopy.Order'])),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=20, unique=True, null=True)),
            ('assopy_id', self.gf('django.db.models.fields.CharField')(max_length=22, unique=True, null=True, blank=True)),
            ('emit_date', self.gf('django.db.models.fields.DateField')()),
            ('payment_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=6, decimal_places=2)),
            ('vat', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.Vat'])),
            ('note', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'assopy', ['Invoice'])

        # Adding model 'CreditNote'
        db.create_table(u'assopy_creditnote', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('invoice', self.gf('django.db.models.fields.related.ForeignKey')(related_name='credit_notes', to=orm['assopy.Invoice'])),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=20)),
            ('assopy_id', self.gf('django.db.models.fields.CharField')(max_length=22, null=True)),
            ('emit_date', self.gf('django.db.models.fields.DateField')()),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=6, decimal_places=2)),
        ))
        db.send_create_signal(u'assopy', ['CreditNote'])

        # Adding model 'RefundOrderItem'
        db.create_table(u'assopy_refundorderitem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('orderitem', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.OrderItem'])),
            ('refund', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.Refund'])),
        ))
        db.send_create_signal(u'assopy', ['RefundOrderItem'])

        # Adding unique constraint on 'RefundOrderItem', fields ['orderitem', 'refund']
        db.create_unique(u'assopy_refundorderitem', ['orderitem_id', 'refund_id'])

        # Adding model 'Refund'
        db.create_table(u'assopy_refund', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('invoice', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.Invoice'], null=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('done', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('credit_note', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['assopy.CreditNote'], unique=True, null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=8)),
            ('reason', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('internal_note', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('reject_reason', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'assopy', ['Refund'])


    def backwards(self, orm):
        # Removing unique constraint on 'RefundOrderItem', fields ['orderitem', 'refund']
        db.delete_unique(u'assopy_refundorderitem', ['orderitem_id', 'refund_id'])

        # Removing unique constraint on 'VatFare', fields ['fare', 'vat']
        db.delete_unique(u'assopy_vatfare', ['fare_id', 'vat_id'])

        # Deleting model 'Country'
        db.delete_table(u'assopy_country')

        # Deleting model 'Token'
        db.delete_table(u'assopy_token')

        # Deleting model 'User'
        db.delete_table(u'assopy_user')

        # Deleting model 'UserIdentity'
        db.delete_table(u'assopy_useridentity')

        # Deleting model 'UserOAuthInfo'
        db.delete_table(u'assopy_useroauthinfo')

        # Deleting model 'Coupon'
        db.delete_table(u'assopy_coupon')

        # Removing M2M table for field fares on 'Coupon'
        db.delete_table(db.shorten_name(u'assopy_coupon_fares'))

        # Deleting model 'Vat'
        db.delete_table(u'assopy_vat')

        # Deleting model 'VatFare'
        db.delete_table(u'assopy_vatfare')

        # Deleting model 'Order'
        db.delete_table(u'assopy_order')

        # Deleting model 'OrderItem'
        db.delete_table(u'assopy_orderitem')

        # Deleting model 'InvoiceLog'
        db.delete_table(u'assopy_invoicelog')

        # Deleting model 'Invoice'
        db.delete_table(u'assopy_invoice')

        # Deleting model 'CreditNote'
        db.delete_table(u'assopy_creditnote')

        # Deleting model 'RefundOrderItem'
        db.delete_table(u'assopy_refundorderitem')

        # Deleting model 'Refund'
        db.delete_table(u'assopy_refund')


    models = {
        u'assopy.country': {
            'Meta': {'ordering': "['name']", 'object_name': 'Country'},
            'iso': ('django.db.models.fields.CharField', [], {'max_length': '2', 'primary_key': 'True'}),
            'iso3': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'numcode': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'printable_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'vat_company': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'vat_company_verify': ('django.db.models.fields.CharField', [], {'default': "'-'", 'max_length': '1'}),
            'vat_person': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'assopy.coupon': {
            'Meta': {'object_name': 'Coupon'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'conference': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Conference']"}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'end_validity': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'fares': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['conference.Fare']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'items_per_usage': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'max_usage': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'start_validity': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.User']", 'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '8'})
        },
        u'assopy.creditnote': {
            'Meta': {'object_name': 'CreditNote'},
            'assopy_id': ('django.db.models.fields.CharField', [], {'max_length': '22', 'null': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'emit_date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'credit_notes'", 'to': u"orm['assopy.Invoice']"}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'})
        },
        u'assopy.invoice': {
            'Meta': {'object_name': 'Invoice'},
            'assopy_id': ('django.db.models.fields.CharField', [], {'max_length': '22', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '20', 'unique': 'True', 'null': 'True'}),
            'emit_date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'invoices'", 'to': u"orm['assopy.Order']"}),
            'payment_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'}),
            'vat': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Vat']"})
        },
        u'assopy.invoicelog': {
            'Meta': {'object_name': 'InvoiceLog'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Invoice']", 'null': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Order']", 'null': 'True'})
        },
        u'assopy.order': {
            'Meta': {'object_name': 'Order'},
            '_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'assopy_id': ('django.db.models.fields.CharField', [], {'max_length': '22', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'billing_notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'card_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'cf_code': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Country']", 'null': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'payment_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'orders'", 'to': u"orm['assopy.User']"}),
            'vat_number': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'})
        },
        u'assopy.orderitem': {
            'Meta': {'object_name': 'OrderItem'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Order']"}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'}),
            'ticket': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['conference.Ticket']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'vat': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Vat']"})
        },
        u'assopy.refund': {
            'Meta': {'object_name': 'Refund'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'credit_note': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['assopy.CreditNote']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'done': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'internal_note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Invoice']", 'null': 'True'}),
            'items': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['assopy.OrderItem']", 'through': u"orm['assopy.RefundOrderItem']", 'symmetrical': 'False'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'reject_reason': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '8'})
        },
        u'assopy.refundorderitem': {
            'Meta': {'unique_together': "(('orderitem', 'refund'),)", 'object_name': 'RefundOrderItem'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'orderitem': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.OrderItem']"}),
            'refund': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Refund']"})
        },
        u'assopy.token': {
            'Meta': {'object_name': 'Token'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'ctype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'payload': ('django.db.models.fields.TextField', [], {'blank': "''"}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '36', 'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'})
        },
        u'assopy.user': {
            'Meta': {'object_name': 'User'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'assopy_id': ('django.db.models.fields.CharField', [], {'max_length': '22', 'unique': 'True', 'null': 'True'}),
            'card_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'cf_code': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Country']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'assopy_user'", 'unique': 'True', 'to': u"orm['auth.User']"}),
            'vat_number': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'})
        },
        u'assopy.useridentity': {
            'Meta': {'object_name': 'UserIdentity'},
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'birthday': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'display_name': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'primary_key': 'True'}),
            'phoneNumber': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'photo': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identities'", 'to': u"orm['assopy.User']"})
        },
        u'assopy.useroauthinfo': {
            'Meta': {'object_name': 'UserOAuthInfo'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'service': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'oauth_infos'", 'to': u"orm['assopy.User']"})
        },
        u'assopy.vat': {
            'Meta': {'object_name': 'Vat'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '125', 'null': 'True', 'blank': 'True'}),
            'fares': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['conference.Fare']", 'null': 'True', 'through': u"orm['assopy.VatFare']", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice_notice': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.DecimalField', [], {'max_digits': '2', 'decimal_places': '0'})
        },
        u'assopy.vatfare': {
            'Meta': {'unique_together': "(('fare', 'vat'),)", 'object_name': 'VatFare'},
            'fare': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Fare']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'vat': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Vat']"})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'conference.conference': {
            'Meta': {'object_name': 'Conference'},
            'cfp_end': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'cfp_start': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'primary_key': 'True'}),
            'conference_end': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'conference_start': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voting_end': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'voting_start': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'})
        },
        u'conference.fare': {
            'Meta': {'unique_together': "(('conference', 'code'),)", 'object_name': 'Fare'},
            'blob': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'end_validity': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'payment_type': ('django.db.models.fields.CharField', [], {'default': "'p'", 'max_length': '1'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'}),
            'recipient_type': ('django.db.models.fields.CharField', [], {'default': "'p'", 'max_length': '1'}),
            'start_validity': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'ticket_type': ('django.db.models.fields.CharField', [], {'default': "'conference'", 'max_length': '10', 'db_index': 'True'})
        },
        u'conference.ticket': {
            'Meta': {'object_name': 'Ticket'},
            'fare': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Fare']"}),
            'frozen': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ticket_type': ('django.db.models.fields.CharField', [], {'default': "'standard'", 'max_length': '8'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['assopy']