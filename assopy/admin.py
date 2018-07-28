# -*- coding: UTF-8 -*-
from django import forms
from django import http
from django import template
from django.conf import settings as dsettings
from django.conf.urls import url, patterns
from django.contrib import admin
from django.core import urlresolvers
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.utils.safestring import mark_safe
from assopy import models
from collections import defaultdict
from datetime import datetime

class CountryAdmin(admin.ModelAdmin):
    list_display = ('printable_name', 'vat_company', 'vat_company_verify', 'vat_person')
    list_editable = ('vat_company', 'vat_company_verify', 'vat_person')
    search_fields = ('name', 'printable_name', 'iso', 'numcode')

admin.site.register(models.Country, CountryAdmin)

class ReadOnlyWidget(forms.widgets.HiddenInput):

    # MAL: This widget doesn't render well in Django 1.8. See #539

    def __init__(self, display=None, *args, **kwargs):
        self.display = display
        super(ReadOnlyWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        output = []
        output.append(u'<span>%s</span>' % (self.display or value))
        output.append(super(ReadOnlyWidget, self).render(name, value, attrs))
        return mark_safe(u''.join(output))

class OrderItemInlineAdmin(admin.TabularInline):
    model = models.OrderItem
    raw_id_fields = ('ticket',)
    readonly_fields = ('ticket', 'price', 'vat', 'code', 'description')

    def get_formset(self, request, obj=None, **kwargs):
        # se ho emesso un invoice impedisco di variare gli order items
        if obj and obj.invoices.exclude(payment_date=None).exists():
            self.can_delete = False
            self.max_num = obj.invoices.exclude(payment_date=None).count()
        else:
            self.can_delete = True
            self.max_num = None
        return super(OrderItemInlineAdmin, self).get_formset(request, obj, **kwargs)

class OrderAdminForm(forms.ModelForm):
    method = forms.ChoiceField(choices=(
        ('admin', 'Admin'),
        ('paypal', 'PayPal'),
        ('cc', 'Credit Card'),
        ('bank', 'Bank'),
    ))

    class Meta:
        model = models.Order
        exclude = ('method',)

    def __init__(self, *args, **kwargs):
        super(OrderAdminForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = models.User.objects.all().select_related('user')
        if self.initial:
            self.fields['method'].initial = self.instance.method

    def clean_assopy_id(self):
        aid = self.cleaned_data.get('assopy_id')
        if aid == '':
            aid = None
        return aid

    def save(self, *args, **kwargs):
        self.instance.method = self.cleaned_data['method']
        return super(OrderAdminForm, self).save(*args, **kwargs)


class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'code', '_user', '_email',
        '_created', 'method',
        '_items', '_complete', '_invoice',
        '_total_nodiscount', '_discount', '_total_payed',
        'stripe_charge_id'
    )
    list_select_related = True
    list_filter = ('method', '_complete',)
    raw_id_fields = ('user',)
    search_fields = (
        'code', 'card_name',
        'user__user__first_name', 'user__user__last_name', 'user__user__email',
        'billing_notes',
    )
    readonly_fields = ['payment_date']
    date_hierarchy = 'created'
    actions = ('do_edit_invoices',)

    form = OrderAdminForm

    inlines = (
        OrderItemInlineAdmin,
    )

    def has_delete_permission(self, request, obj=None):
        # se ho emesso un invoice impedisco di cancellare l'ordine
        if obj and obj.invoices.exclude(payment_date=None).exists():
            return False
        else:
            return super(OrderAdmin, self).has_delete_permission(request, obj)

    def get_actions(self, request):
        # elimino l'action delete per costringere l'utente ad usare il pulsante
        # nella pagina di dettaglio. La differenza tra il pulsante e questa
        # azione che l'ultima non chiama la `.delete()` del modello.
        actions = super(OrderAdmin, self).get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def _user(self, o):
        url = urlresolvers.reverse('admin:auth_user_change', args=(o.user.user_id,))
        name = '%s %s' % (o.user.user.first_name, o.user.user.last_name)
        html = '<a href="%s">%s</a>' % (url, name)
        if name != o.card_name:
            html += ' - ' + o.card_name
        return html
    _user.short_description = 'buyer'
    _user.allow_tags = True
    _user.admin_order_field = 'user__user__last_name'

    def _email(self, o):
        return '<a href="mailto:%s">%s</a>' % (o.user.user.email, o.user.user.email)
    _email.short_description = 'buyer email'
    _email.allow_tags = True
    _email.admin_order_field = 'user__user__email'

    def _items(self, o):
        return o.orderitem_set.exclude(ticket=None).count()
    _items.short_description = '#Tickets'

    def _created(self, o):
        return o.created.strftime('%d %b %Y - %H:%M:%S')
    _created.admin_order_field = 'created'

    def _total_nodiscount(self, o):
        return o.total(apply_discounts=False)
    _total_nodiscount.short_description = 'Total'

    def _discount(self, o):
        return o.total(apply_discounts=False) - o.total()
    _discount.short_description = 'Discount'

    def _total_payed(self, o):
        return o.total()
    _total_payed.short_description = 'Payed'

    def _invoice(self, o):
        from django.contrib.admin.util import quote
        output = []
        # MAL: PDF generation is slower, so default to HTML
        if 1 or dsettings.DEBUG:
            vname = 'assopy-invoice-html'
        else:
            vname = 'assopy-invoice-pdf'
        for i in o.invoices.all():
            url = urlresolvers.reverse(
                vname, kwargs={
                    'order_code': quote(o.code),
                    'code': quote(i.code),
                }
            )
            output.append(
                '<a href="%s">%s%s</a>' % (
                    url, i.code, ' *' if not i.payment_date else '')
            )
        return ' '.join(output)
    _invoice.allow_tags = True
    _invoice.admin_order_field = 'invoices'

    def get_urls(self):
        urls = super(OrderAdmin, self).get_urls()
        f = self.admin_site.admin_view
        my_urls = patterns('',
            url(r'^invoices/$', f(self.edit_invoices), name='assopy-edit-invoices'),
            url(r'^stats/$', f(self.stats), name='assopy-order-stats'),
            url(r'^vouchers/$', f(self.vouchers), name='assopy-order-vouchers'),
            url(r'^vouchers/(?P<conference>[\w-]+)/(?P<fare>[\w-]+)/$', f(self.vouchers_fare), name='assopy-order-vouchers-fare'),
        )
        return my_urls + urls

    def vouchers(self, request):
        from conference.models import Fare
        ctx = {
            'fares': Fare.objects\
                .filter(conference=dsettings.CONFERENCE_CONFERENCE, payment_type='v'),
        }
        return render_to_response(
            'admin/assopy/order/vouchers.html', ctx, context_instance=template.RequestContext(request))

    def vouchers_fare(self, request, conference, fare):
        items = models.OrderItem.objects\
            .filter(ticket__fare__conference=conference, ticket__fare__code=fare)\
            .filter(Q(order___complete=True)|Q(order__method='bank'))\
            .select_related('ticket__fare', 'order__user__user')
        ctx = {
            'items': items,
        }
        return render_to_response(
            'admin/assopy/order/vouchers_fare.html', ctx, context_instance=template.RequestContext(request))

    def do_edit_invoices(self, request, queryset):
        ids = [ str(o.id) for o in queryset ]
        if ids:
            url = urlresolvers.reverse('admin:assopy-edit-invoices') + '?id=' + ','.join(ids)
            return redirect(url)
        else:
            self.message_user(request, 'no orders')
    do_edit_invoices.short_description = 'Edit/Make invoices'

    def edit_invoices(self, request):
        try:
            ids = map(int, request.GET['id'].split(','))
        except KeyError:
            return http.HttpResponseBadRequest('orders id missing')
        except ValueError:
            return http.HttpResponseBadRequest('invalid id list')
        orders = models.Order.objects.filter(id__in=ids)
        if not orders.count():
            return redirect('admin:assopy_order_changelist')

        class FormPaymentDate(forms.Form):
            date = forms.DateField(input_formats=('%Y/%m/%d',), help_text='Enter the date (YYYY/MM/DD) of receipt of payment. Leave blank to issue an invoice without a payment', required=False)

        if request.method == 'POST':
            form = FormPaymentDate(data=request.POST)
            if form.is_valid():
                d = form.cleaned_data['date']
                for o in orders:
                    o.confirm_order(d)
                    o.complete()
                return redirect('admin:assopy_order_changelist')
        else:
            form = FormPaymentDate()
        ctx = {
            'orders': orders,
            'form': form,
            'ids': request.GET.get('id'),
        }
        return render_to_response('assopy/admin/edit_invoices.html', ctx, context_instance=template.RequestContext(request))

    def stats_conference(self, conf):
        from assopy import stats
        from django.template import Template, Context

        l = (
            stats.movimento_cassa,
            stats.prezzo_biglietti_ricalcolato,
        )
        output = []
        for f in l:
            if hasattr(f, 'short_description'):
                name = f.short_description
            else:
                name = f.__name__.replace('_', ' ').strip()

            if hasattr(f, 'description'):
                doc = f.description
            else:
                doc = f.__doc__

            if hasattr(f, 'template'):
                tpl = f.template
            else:
                tpl = '{{ data }}'

            def render(f=f, tpl=tpl):
                ctx = Context({'data': f(year=conf.conference_start.year) })
                return Template(tpl).render(ctx)

            output.append((name, doc, render))
        return output

    def stats(self, request):
        from conference.models import Conference

        ctx = {
            'conferences': [],
        }
        for c in Conference.objects.order_by('-conference_start')[:3]:
            ctx['conferences'].append((c, self.stats_conference(c)))

        return render_to_response('assopy/admin/order_stats.html', ctx, context_instance=template.RequestContext(request))

admin.site.register(models.Order, OrderAdmin)

class CouponAdminForm(forms.ModelForm):
    class Meta:
        model = models.Coupon
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CouponAdminForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = models.User.objects\
            .all()\
            .select_related('user')\
            .order_by('user__first_name', 'user__last_name')

        if self.instance:
            from conference.models import Fare
            if self.instance.pk:
                self.fields['fares'].queryset = Fare.objects.filter(conference=self.instance.conference_id)
            else:
                self.fields['fares'].queryset = Fare.objects.filter(conference=dsettings.CONFERENCE_CONFERENCE)

    def clean_code(self):
        return self.cleaned_data['code'].upper()

class CouponValidListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'validity'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'valid'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'valid coupon'),
            ('no', 'used / invalid coupon'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'no':
            result = False
        elif self.value() == 'yes':
            result = True
        else:
            # No filter
            return queryset
        ids = [coupon.id
               for coupon in queryset
               if bool(coupon.valid(coupon.user)) is result]
        return queryset.filter(id__in=ids)

class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'value', 'start_validity', 'end_validity', 'max_usage', 'items_per_usage', '_user', '_valid', '_usage')
    search_fields = ('code', 'user__user__first_name', 'user__user__last_name', 'user__user__email',)
    list_filter = ('conference',
                   CouponValidListFilter,
                   'value',
                   )
    form = CouponAdminForm

    def get_queryset(self, request):
        qs = super(CouponAdmin, self).get_queryset(request)
        qs = qs.select_related('user__user')
        return qs

    def changelist_view(self, request, extra_context=None):
        if not request.GET.has_key('conference__code__exact'):
            q = request.GET.copy()
            q['conference__code__exact'] = dsettings.CONFERENCE_CONFERENCE
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(CouponAdmin,self).changelist_view(request, extra_context=extra_context)

    def _user(self, o):
        if not o.user:
            return ''
        url = urlresolvers.reverse('admin:auth_user_change', args=(o.user.user_id,))
        return '<a href="%s">%s</a> (<a href="mailto:%s">email</a>)' % (url, o.user.name(), o.user.user.email)
    _user.short_description = 'user'
    _user.allow_tags = True

    def _usage(self, o):
        return models.OrderItem.objects.filter(ticket=None, code=o.code).count()
    _usage.short_description = 'usage'

    def _valid(self, o):
        return o.valid(o.user)
    _valid.short_description = 'valid'
    _valid.boolean = True

admin.site.register(models.Coupon, CouponAdmin)

from django.contrib.auth.models import User as aUser
from django.contrib.auth.admin import UserAdmin as aUserAdmin

admin.site.unregister(aUser)
class AuthUserAdmin(aUserAdmin):
    list_display = aUserAdmin.list_display + ('_doppelganger',)

    def get_urls(self):
        f = self.admin_site.admin_view
        urls = patterns('',
            url(r'^(?P<uid>\d+)/login/$', f(self.create_doppelganger), name='auser-create-doppelganger'),
            url(r'^(?P<uid>\d+)/order/$', f(self.new_order), name='auser-order'),
            url(r'^kill_doppelganger/$', self.kill_doppelganger, name='auser-kill-doppelganger'),
        )
        return urls + super(AuthUserAdmin, self).get_urls()

    def create_doppelganger(self, request, uid):
        # user è l'utente corrente, quello che vuole creare un doppelganger.
        # salvo nella sessione del nuovo utente i dati che mi servono per
        # conoscere chi sta controllando il doppelganger.
        user = request.user
        udata = (user.id, '%s %s' % (user.first_name, user.last_name),)

        from django.contrib import auth
        auth.logout(request)
        user = auth.authenticate(uid=uid)
        auth.login(request, user)
        request.session['doppelganger'] = udata

        return http.HttpResponseRedirect(urlresolvers.reverse('assopy-tickets'))

    def kill_doppelganger(self, request):
        uid = request.session.pop('doppelganger')[0]

        from django.contrib import auth
        auth.logout(request)
        user = auth.authenticate(uid=uid)
        if user.is_superuser:
            auth.login(request, user)
        return http.HttpResponseRedirect('/')

    def new_order(self, request, uid):
        from assopy import forms as aforms
        from conference.models import Fare
        from conference.settings import CONFERENCE

        user = get_object_or_404(models.User, user=uid)

        class FormTickets(aforms.FormTickets):
            coupon = forms.CharField(label='Coupon(s)', required=False)
            country = forms.CharField(max_length=2, required=False)
            address = forms.CharField(max_length=150, required=False)
            card_name = forms.CharField(max_length=200, required=True, initial=user.card_name or user.name())
            billing_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
            remote = forms.BooleanField(required=False, initial=True, help_text='debug only, fill the order on the remote backend')
            def __init__(self, *args, **kwargs):
                super(FormTickets, self).__init__(*args, **kwargs)
                self.fields['payment'].choices = (('admin', 'Admin'),) + tuple(self.fields['payment'].choices)
                self.fields['payment'].initial = 'admin'

            def available_fares(self):
                return Fare.objects.available(conference=CONFERENCE)

            def clean_country(self):
                data = self.cleaned_data.get('country')
                if data:
                    try:
                        data = models.Country.objects.get(pk=data)
                    except models.Country.DoesNotExist:
                        raise forms.ValidationError('Invalid country: %s' % data)
                return data

            def clean_coupon(self):
                data = self.cleaned_data.get('coupon')
                output = []
                if data:
                    for c in data.split(' '):
                        try:
                            output.append(models.Coupon.objects.get(conference=CONFERENCE, code=c))
                        except models.Coupon.DoesNotExist:
                            raise forms.ValidationError('invalid coupon "%s"' % c)
                if self.cleaned_data.get('payment') == 'admin':
                    for c in output:
                        if c.value != '100%':
                            raise forms.ValidationError('admin orders must have a 100% discount coupon')
                return output

        if request.method == 'POST':
            form = FormTickets(data=request.POST)
            if form.is_valid():
                data = form.cleaned_data
                # non salvo l'utente per non sovrascrivere il suo card_name
                user.card_name = data['card_name']
                models.Order.objects.create(
                    user=user,
                    payment=data['payment'],
                    items=data['tickets'],
                    billing_notes=data['billing_notes'],
                    coupons=data['coupon'],
                    remote=data['remote'],
                    country=data['country'],
                    address=data['address'],
                )
                return redirect('admin:auth_user_change', user.user_id,)
        else:
            form = FormTickets()
        ctx = {
            'user': user,
            'form': form,
        }
        return render_to_response('admin/auth/user/new_order.html', ctx, context_instance=template.RequestContext(request))

    def _doppelganger(self, o):
        url = urlresolvers.reverse('admin:auser-create-doppelganger', kwargs={'uid': o.id})
        return '<a href="%s" target="_blank">become this user</a>' % url
    _doppelganger.allow_tags = True
    _doppelganger.short_description = 'Doppelganger'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        from assopy import dataaccess
        ctx = extra_context or {}
        ctx['user_data'] = dataaccess.all_user_data(object_id)
        return super(AuthUserAdmin, self).change_view(request, object_id, form_url, ctx)

admin.site.register(aUser, AuthUserAdmin)

class RefundAdminForm(forms.ModelForm):
    class Meta:
        model = models.Refund
        exclude = ('done', 'invoice', 'credit_note')

class RefundAdmin(admin.ModelAdmin):
    list_display = ('_user', 'reason', '_status', '_order', '_invoice', '_cnote', '_items', '_total', 'created', 'done')
    form = RefundAdminForm

    def get_queryset(self, request):
        qs = super(RefundAdmin, self).get_queryset(request)

        orderitems = defaultdict(list)
        items = models.RefundOrderItem.objects\
            .filter(refund__in=qs)\
            .select_related('orderitem__order__user__user')
        for row in items:
            orderitems[row.refund_id].append(row.orderitem)
        self.orderitems = orderitems

        qs = qs.select_related('invoice__order', 'credit_note')
        return qs

    def _user(self, o):
        data = self.orderitems[o.id]
        if not data:
            return "[[ ERROR, no items ]]"
        else:
            u = data[0].order.user.user
            links = [
                '%s %s</a> (' % (u.first_name, u.last_name),
                '<a href="%s" title="user page">U</a>, ' % urlresolvers.reverse('admin:auth_user_change', args=(u.id,)),
                '<a href="%s" title="doppelganger" target="_blank">D</a>)' % urlresolvers.reverse('admin:auser-create-doppelganger', kwargs={'uid': u.id}),
            ]
            return ' '.join(links)
    _user.allow_tags = True
    _user.admin_order_field = 'orderitem__order__user__user__first_name'

    def _order(self, o):
        data = self.orderitems[o.id]
        if data:
            url = urlresolvers.reverse('admin:assopy_order_change', args=(data[0].order.id,))
            return '<a href="%s">%s</a> del %s' % (url, data[0].order.code, data[0].order.created.strftime('%Y-%m-%d'))
        else:
            return ''
    _order.allow_tags = True

    def _invoice(self, o):
        i = o.invoice
        if not i:
            return ''
        rev = urlresolvers.reverse
        url = rev('admin:assopy_invoice_change', args=(i.id,))
        download = rev('assopy-invoice-pdf', kwargs={'order_code': i.order.code, 'code': i.code})
        return '<a href="%s">%s</a> (<a href="%s">pdf</a>)' % (url, i, download)

    _invoice.allow_tags = True

    def _cnote(self, o):
        c = o.credit_note
        if not c:
            return ''
        rev = urlresolvers.reverse
        download = rev('assopy-credit_note-pdf', kwargs={'order_code': o.invoice.order.code, 'code': c.code})
        return '%s (<a href="%s">pdf</a>)' % (c, download)
    _cnote.allow_tags = True

    def _items(self, o):
        data = self.orderitems[o.id]
        output = []
        for item in data:
            output.append('<li>%s - %s</li>' % (item.description, item.price))
        return '<ul>%s</ul>' % ''.join(output)
    _items.allow_tags = True

    def _total(self, o):
        data = self.orderitems[o.id]
        total = 0
        for item in data:
            total += item.price
        return '%.2f€' % total

    def _status(self, o):
        if o.status in ('refunded', 'rejected'):
            return '<span style="color: green">%s</span>' % o.status
        elif o.status == 'pending':
            return '<span style="color: red; font-weight: bold;">%s</span>' % o.status
        else:
            return '<span style="color: orange">%s</span>' % o.status
    _status.allow_tags = True

    def save_model(self, request, obj, form, change):
        if obj.id:
            obj.old_status = models.Refund.objects\
                .values('status')\
                .get(id=obj.id)['status']
            obj.old_tickets = list(obj.items.all().values_list('ticket', flat=True))
        else:
            obj.old_status = None
            obj.old_tickets = []
        return super(RefundAdmin, self).save_model(request, obj, form,change)

    def save_formset(self, request, form, formset, change):
        # non posso usare il formset perché parla di RefundCreditNote mentre io
        # voglio manipolare direttamente le CreditNote, chiamo però la
        # .save(commit=False) per fargli popolare lo stato interno e far
        # contento l'admin di django
        formset.save(commit=False)
        refund = form.instance
        notes = dict([(x.assopy_id, x)
            for x in models.CreditNote.objects\
                .filter(refundcreditnote__refund=refund)])
        for item in formset.cleaned_data:
            if not item:
                continue
            if item['DELETE']:
                item['id'].credit_note.delete()
            else:
                try:
                    cn = notes.pop(item['assopy_id'])
                except KeyError:
                    cn = models.CreditNote(assopy_id=item['assopy_id'])
                    total = sum(refund.items.all().values_list('price', flat=True))
                    cn.price = total
                    cn.emit_date = datetime.now()
                    cn.code = item['code']
                    cn.invoice = item['invoice']
                    cn.save()

                    r = models.RefundCreditNote(refund=refund)
                    r.credit_note = cn
                    r.save()
                else:
                    assert cn.refundcreditnote.refund == refund
                    cn.code = item['code']
                    cn.invoice = item['invoice']
                    cn.save()

        # Emetto il segnale da qui perché sono sicuro che le credit_note sono
        # collegate al refund. Ovviamente mi perdo il segnale emesso quando il
        # Refund viene creato tramite frontend, quel caso dovrà essere gestito
        # in maniera speaciale
        models.refund_event.send(sender=refund, old=refund.old_status, tickets=refund.old_tickets)

admin.site.register(models.Refund, RefundAdmin)


class InvoiceAdminForm(forms.ModelForm):
    class Meta:
        model = models.Invoice
        exclude = ("assopy_id",)
        widgets = {
            'price':ReadOnlyWidget,
            'vat' : ReadOnlyWidget,
            'order' : ReadOnlyWidget
        }

class InvoiceAdmin(admin.ModelAdmin):
    actions = ('do_csv_invoices',)
    list_display = ('__unicode__', '_invoice', '_user', 'payment_date', 'price', '_order', 'vat')
    date_hierarchy = 'payment_date'
    search_fields = (
        'code', 'order__code', 'order__card_name',
        'order__user__user__first_name', 'order__user__user__last_name', 'order__user__user__email',
        'order__billing_notes',)
    form = InvoiceAdminForm

    def _order(self, o):
        order = o.order
        url = urlresolvers.reverse('admin:assopy_order_change', args=(order.id,))
        return '<a href="%s">%s</a>' % (url, order.code)
    _order.allow_tags = True
    _order.admin_order_field = 'order'

    def _user(self, o):
        u = o.order.user.user
        name = '%s %s' % (u.first_name, u.last_name)
        admin_url = urlresolvers.reverse('admin:auth_user_change', args=(u.id,))
        dopp_url = urlresolvers.reverse('admin:auser-create-doppelganger', kwargs={'uid': u.id})
        html = '<a href="%s">%s</a> (<a href="%s">D</a>)' % (admin_url, name, dopp_url)
        if o.order.card_name != name:
            html += ' - ' + o.order.card_name
        return html
    _user.allow_tags = True
    _user.admin_order_field = 'order__user__user__first_name'

    def _invoice(self, i):
        fake = not i.payment_date
        view = urlresolvers.reverse('assopy-invoice-html', kwargs={'order_code': i.order.code, 'code': i.code})
        download = urlresolvers.reverse('assopy-invoice-pdf', kwargs={'order_code': i.order.code, 'code': i.code})
        return '<a href="%s">View</a> - <a href="%s">Download</a> %s' % (view, download, '[Not payed]' if fake else '')
    _invoice.allow_tags = True
    _invoice.short_description = 'Download'

    def has_delete_permission(self, request, obj=None):
        if obj and obj.payment_date != None:
            return False
        else:
            return super(InvoiceAdmin, self).has_delete_permission(request, obj)

    def do_csv_invoices(self, request, queryset):
        import csv
        from cStringIO import StringIO
        columns = (
                'numero', 'Card name',
                'Customer:tipo IVA', 'Customer:Customer Type',
                'Codice Fiscale', 'Partita IVA', 'Nazione',
                'prezzo netto', 'IVA', 'Gross Price',
                'Invoice Date', 'Payment date',
                'Deposit Invoice', 'SIM Invoice', 'Voucher Invoice',
                'Billing notes')

        def e(d):
            for k, v in d.items():
                d[k] = v.encode('utf-8')
            return d

        ofile = StringIO()
        writer = csv.DictWriter(ofile, fieldnames=columns)
        writer.writerow(dict(zip(columns, columns)))
        for i in queryset.select_related('order', 'vat'):
            writer.writerow(e({
                'numero': i.code,
                'Card name': i.order.card_name,
                'Customer:tipo IVA': i.vat.invoice_notice,
                'Customer:Customer Type': '',
                'Codice Fiscale': i.order.cf_code,
                'Partita IVA': i.order.vat_number,
                'Nazione': i.order.country_id,
                'prezzo netto': '%.2f' % i.net_price(),
                'IVA': '%.2f' % i.vat_value(),
                'Gross Price': '%.2f' % i.price,
                'Invoice Date': i.emit_date.strftime('%d-%m-%Y'),
                'Payment date': i.payment_date.strftime('%d-%m-%Y'),
                'Deposit Invoice': '',
                'SIM Invoice': '',
                'Voucher Invoice': '',
                'Billing notes': i.order.billing_notes,
            }))

        response = http.HttpResponse(ofile.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=fatture.csv'
        return response
    do_csv_invoices.short_description = 'Download invoices as csv'


admin.site.register(models.Invoice,InvoiceAdmin)

admin.site.register(models.Vat)

class InvoiceLogAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'order', 'invoice','date'
    )

admin.site.register(models.InvoiceLog, InvoiceLogAdmin)

from conference import admin as cadmin

class AssopyFareForm(forms.ModelForm):
    vat = forms.ModelChoiceField(queryset=models.Vat.objects.all())

    class Meta:
        model = cadmin.models.Fare
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance',None)
        if instance:
            try:
                vat = instance.vat_set.all()[0]
                initial = kwargs.get('initial',{})
                initial.update({'vat' : vat })
                kwargs['initial'] = initial
            except  IndexError:
                pass
        super(AssopyFareForm, self).__init__(*args, **kwargs)

class AssopyFareAdmin(cadmin.FareAdmin):
    form = AssopyFareForm
    list_display = cadmin.FareAdmin.list_display + ('_vat',)

    def _vat(self,obj):
        try:
            return obj.vat_set.all()[0]
        except IndexError:
            return None
    _vat.short_description = 'VAT'

    def save_model(self, request, obj, form, change):
        super(AssopyFareAdmin, self).save_model(request, obj, form, change)
        if 'vat' in form.cleaned_data:
            # se la tariffa viene modificata dalla list_view 'vat' potrebbe
            # non esserci
            vat_fare, created = models.VatFare.objects.get_or_create(
                fare=obj, defaults={'vat': form.cleaned_data['vat']})
            if not created and vat_fare.vat != form.cleaned_data['vat']:
                vat_fare.vat = form.cleaned_data['vat']
                vat_fare.save()

admin.site.unregister(cadmin.models.Fare)
admin.site.register(cadmin.models.Fare, AssopyFareAdmin)
