# -*- coding: UTF-8 -*-
from django import forms
from django import http
from django import template
from django.conf import settings as dsettings
from django.conf.urls.defaults import url, patterns
from django.contrib import admin
from django.core import urlresolvers
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.utils.safestring import mark_safe
from assopy import models, settings
if settings.GENRO_BACKEND:
    from assopy.clients import genro
from collections import defaultdict
from datetime import datetime

class CountryAdmin(admin.ModelAdmin):
    list_display = ('printable_name', 'vat_company', 'vat_company_verify', 'vat_person')
    list_editable = ('vat_company', 'vat_company_verify', 'vat_person')
    search_fields = ('name', 'printable_name', 'iso', 'numcode')

admin.site.register(models.Country, CountryAdmin)

class ReadOnlyWidget(forms.widgets.HiddenInput):

    def __init__(self, display=None, *args, **kwargs):
        self.display = display
        super(ReadOnlyWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None):
        output = []
        output.append('<span>%s</span>' % self.display or value)
        output.append(super(ReadOnlyWidget, self).render(name, value, attrs))
        return mark_safe(u''.join(output))

class OrderItemAdminForm(forms.ModelForm):
    class Meta:
        model = models.OrderItem

    def __init__(self, *args, **kwargs):
        super(OrderItemAdminForm, self).__init__(*args, **kwargs)
        from conference.models import Ticket
        self.fields['ticket'].queryset = Ticket.objects.all().select_related('fare')
        instance = kwargs.get('instance',None)
        if instance and instance.order.invoices.exclude(payment_date=None).exists():
            # se ho emesso un invoice impedisco di variare alcuni campi degli gli order items
            for f in ('ticket', 'price', 'vat', 'code'):
                self.fields[f].widget = ReadOnlyWidget(display = getattr(self.instance, f))

class OrderItemInlineAdmin(admin.TabularInline):
    model = models.OrderItem
    form = OrderItemAdminForm

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

    def save(self, *args, **kwargs):
        self.instance.method = self.cleaned_data['method']
        return super(OrderAdminForm, self).save(*args, **kwargs)

class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'code', '_user', '_email',
        'card_name', '_created', 'method',
        '_items', '_complete', '_invoice',
        '_total_nodiscount', '_discount', '_total_payed',
    )
    list_select_related = True
    list_filter = ('method', '_complete',)
    list_per_page = 20
    search_fields = (
        'code', 'card_name',
        'user__user__first_name', 'user__user__last_name', 'user__user__email',
        'billing_notes',
    )
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
        return '<a href="%s">%s</a>' % (url, o.user.name())
    _user.short_description = 'buyer'
    _user.allow_tags = True

    def _email(self, o):
        return '<a href="mailto:%s">%s</a>' % (o.user.user.email, o.user.user.email)
    _email.short_description = 'buyer email'
    _email.allow_tags = True

    def _items(self, o):
        return o.orderitem_set.exclude(ticket=None).count()
    _items.short_description = '#Tickets'

    def _created(self, o):
        return o.created.strftime('%d %b %Y - %H:%M:%S')

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
        output = []
        for i in o.invoices.all():
            if settings.GENRO_BACKEND:
                output.append('<a href="%s">%s%s</a>' % (genro.invoice_url(i.assopy_id), i.code, ' *' if not i.payment_date else ''))
            else:
                output.append('<a href="%s">%s%s</a>' % (urlresolvers.reverse('admin:assopy-view-invoices', kwargs={'id': i.pk }), i, ' *' if not i.payment_date else ''))
        return ' '.join(output)
    _invoice.allow_tags = True

    def get_urls(self):
        urls = super(OrderAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^invoices/(?P<id>\d+)/$', self.admin_site.admin_view(self.view_invoices), name='assopy-view-invoices'),
            url(r'^invoices/$', self.admin_site.admin_view(self.edit_invoices), name='assopy-edit-invoices'),
            url(r'^stats/$', self.admin_site.admin_view(self.stats), name='assopy-order-stats'),
        )
        return my_urls + urls

    def do_edit_invoices(self, request, queryset):
        ids = [ str(o.id) for o in queryset if not o.complete() ]
        if ids:
            url = urlresolvers.reverse('admin:assopy-edit-invoices') + '?id=' + ','.join(ids)
            return redirect(url)
        else:
            self.message_user(request, 'no orders')
    do_edit_invoices.short_description = 'Edit/Make invoices'

    def view_invoices(self, request, id):
        invoice = get_object_or_404(models.Invoice, pk=id)
        return render_to_response('assopy/invoice.html', {'invoice':invoice}, context_instance=template.RequestContext(request))

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
                    if settings.GENRO_BACKEND:
                        genro.confirm_order(o.assopy_id, o.total(), d)
                    else:
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

    def __init__(self, *args, **kwargs):
        super(CouponAdminForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = models.User.objects.all().select_related('user').order_by('user__first_name', 'user__last_name')

    def clean_code(self):
        return self.cleaned_data['code'].upper()

class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'value', 'start_validity', 'end_validity', 'max_usage', 'items_per_usage', '_user', '_valid')
    search_fields = ('code', 'user__user__first_name', 'user__user__last_name', 'user__user__email',)
    list_filter = ('conference',)
    form = CouponAdminForm

    def queryset(self, request):
        qs = super(CouponAdmin, self).queryset(request)
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

    def _valid(self, o):
        return o.valid(o.user)
    _valid.short_description = 'valid (maybe not used?)'
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

    @transaction.commit_on_success
    def new_order(self, request, uid):
        from assopy import forms as aforms
        from conference.models import Fare
        from conference.settings import CONFERENCE

        user = get_object_or_404(models.User, user=uid)

        class FormTickets(aforms.FormTickets):
            coupon = forms.CharField(label='Coupon(s)', required=True)
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

    def change_view(self, request, object_id, extra_context=None):
        from assopy import dataaccess
        ctx = extra_context or {}
        ctx['user_data'] = dataaccess.all_user_data(object_id)
        return super(AuthUserAdmin, self).change_view(request, object_id, ctx)

admin.site.register(aUser, AuthUserAdmin)

# Refund Admin
# ------------
# La form dei rimborsi permette di specificare le note di credito associate al
# rimborso; le note di credito sono collegate tramite una tabella intermedia
# per motivi di performance ma non voglio esporre questo dettaglio all'utente.
# Tutto quello di cui ho bisogno sono tre campi:
#
# - assopy_id
# - codice nota di credito
# - fattura collegata
#
# Qui faccio una cosa un po' arzigogolata, il ModelAdmin e la ModelForm della
# RefundCreditNote espongono e manipolano i dati di una CreditNote e gestisco
# questa cosa nella save_formset di RefundAdmin
class RefundCreditNoteInlineAdminForm(forms.ModelForm):
    code = forms.CharField(label='code', max_length=9)
    assopy_id = forms.CharField(label='assopy id', max_length=22)
    invoice = forms.CharField(label='invoice code', max_length=9)

    class Meta:
        model = models.RefundCreditNote
        fields = ()

    def clean_invoice(self):
        data = self.cleaned_data['invoice']
        try:
            i = models.Invoice.objects.get(code=data)
        except models.Invoice.DoesNotExist:
            raise forms.ValidationError('Invoice does not exist')
        return i

    def __init__(self, *args, **kwargs):
        super(RefundCreditNoteInlineAdminForm, self).__init__(*args, **kwargs)
        if self.instance.credit_note_id:
            self.fields['code'].initial = self.instance.credit_note.code
            self.fields['assopy_id'].initial = self.instance.credit_note.assopy_id
            self.fields['invoice'].initial = self.instance.credit_note.invoice.code

class RefundCreditNoteInlineAdmin(admin.TabularInline):
    model = models.RefundCreditNote
    form = RefundCreditNoteInlineAdminForm
    extra = 1

class RefundAdminForm(forms.ModelForm):
    class Meta:
        model = models.Refund
        exclude = ('done',)

class RefundAdmin(admin.ModelAdmin):
    list_display = ('_user', 'reason', '_order', '_items', '_total', 'created', '_status', 'done')
    form = RefundAdminForm

    inlines = (RefundCreditNoteInlineAdmin,)

    def queryset(self, request):
        qs = super(RefundAdmin, self).queryset(request)
        qs = qs.select_related('orderitem__order__user__user')
        orderitems = defaultdict(list)
        items = models.RefundOrderItem.objects\
            .filter(refund__in=qs)\
            .select_related('orderitem__order')
        for row in items:
            orderitems[row.refund_id].append(row.orderitem)
        self.orderitems = orderitems
        return qs

    def _user(self, o):
        data = self.orderitems[o.id]
        if not data:
            return "ERROR, no items"
        else:
            u = data[0].order.user.user
            links = [
                '%s %s <br/>' % (u.first_name, u.last_name),
                '<a href="%s" title="user page">U</a>' % urlresolvers.reverse('admin:auth_user_change', args=(u.id,)),
                '<a href="%s" title="doppelganger" target="_blank">D</a>' % urlresolvers.reverse('admin:auser-create-doppelganger', kwargs={'uid': u.id}),
            ]
            return ' '.join(links)
    _user.allow_tags = True
    _user.admin_order_field = 'orderitem__order__user__user__first_name'

    def _order(self, o):
        data = self.orderitems[o.id]
        if data:
            url = urlresolvers.reverse('admin:assopy_order_change', args=(data[0].order.id,))
            return '<a href="%s">%s</a>' % (url, data[0].order.code)
        else:
            return ''
    _order.allow_tags = True

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


class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'order', 'vat','payment_date','price')

    def has_delete_permission(self, request, obj=None):
        if obj and obj.payment_date != None:
            return False
        else:
            return super(InvoiceAdmin, self).has_delete_permission(request, obj)


admin.site.register(models.Invoice,InvoiceAdmin)

admin.site.register(models.Vat)

from conference import admin as cadmin

class AssopyFareForm(forms.ModelForm):
    vat = forms.ModelChoiceField(queryset=models.Vat.objects.all())

    class Meta:
        model = cadmin.models.Fare

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance',None)
        if instance:
            try:
                vat = instance.vat_set.all()[0]
                initial = kwargs.get('instance',{})
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
        vat_fares, created = models.Vat_fares.objects.get_or_create(fare=obj, defaults={'vat':form.cleaned_data['vat']})
        if not created and vat_fares.vat != form.cleaned_data['vat']:
            vat_fares.vat = form.cleaned_data['vat']
            vat_fares.save()

admin.site.unregister(cadmin.models.Fare)
admin.site.register(cadmin.models.Fare, AssopyFareAdmin)