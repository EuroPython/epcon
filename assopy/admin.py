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
from assopy import models
from assopy.clients import genro

class CountryAdmin(admin.ModelAdmin):
    list_display = ('printable_name', 'vat_company', 'vat_company_verify', 'vat_person')
    list_editable = ('vat_company', 'vat_company_verify', 'vat_person')
    search_fields = ('name', 'printable_name', 'iso', 'numcode')

admin.site.register(models.Country, CountryAdmin)

class OrderItemAdminForm(forms.ModelForm):
    class Meta:
        model = models.OrderItem

    def __init__(self, *args, **kwargs):
        super(OrderItemAdminForm, self).__init__(*args, **kwargs)
        from conference.models import Ticket
        self.fields['ticket'].queryset = Ticket.objects.all().select_related('fare')

class OrderItemInlineAdmin(admin.TabularInline):
    model = models.OrderItem
    form = OrderItemAdminForm

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

    def get_actions(self, request):
        # elimino l'action delete per costringere l'utente ad usare il pulsante
        # nella pagina di dettaglio. La differenza tra il pulsante e questa
        # azione che l'ultima non chiama la `.delete()` del modello.
        actions = super(OrderAdmin, self).get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def _user(self, o):
        url = urlresolvers.reverse('admin:assopy_user_change', args=(o.user.id,))
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
            output.append('<a href="%s">%s%s</a>' % (genro.invoice_url(i.assopy_id), i.code, ' *' if not i.payment_date else ''))
        return ' '.join(output)
    _invoice.allow_tags = True

    def get_urls(self):
        urls = super(OrderAdmin, self).get_urls()
        my_urls = patterns('',
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
                    genro.confirm_order(o.assopy_id, o.total(), d)
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
        from conference.models import Ticket
        from django.db.models import Sum, Count, Q

        def _orders():
            """
            Ordini completi
            """
            return models.Order.objects\
                .filter(_complete=True, orderitem__ticket__fare__conference=conf.code)\
                .distinct()

        def _tickets():
            """
            Biglietti venduti
            """
            return Ticket.objects\
                .filter(orderitem__order__in=_orders())

        def _order_items_by_fare():
            """
            Dettaglio ordini: raggruppato per tariffa
            """
            return models.OrderItem.objects\
                .filter(order__in=_orders())\
                .values('ticket__fare__code', 'ticket__fare__name')\
                .annotate(total=Sum('price'), count=Count('pk'))\
                .order_by('ticket__fare__code')

        def _order_items_by_ticket():
            """
            Dettaglio ordini: raggruppato per tipo biglietto
            """
            return models.OrderItem.objects\
                .filter(order__in=_orders())\
                .values('ticket__fare__ticket_type')\
                .annotate(total=Sum('price'), count=Count('pk'))\
                .order_by('-total')

        def _order_items_by_recipient():
            """
            Dettaglio ordini: raggruppato per tipo acquirente
            """
            return models.OrderItem.objects\
                .filter(order__in=_orders(), ticket__fare__ticket_type='conference')\
                .values('ticket__fare__recipient_type')\
                .annotate(total=Sum('price'), count=Count('pk'))\
                .order_by('-total')

        def _recalculated_ticket_prices():
            """
            Ricalcola il ricavo dei biglietti eliminando quelli gratuiti e
            ridistribuendo il prezzo sui rimanenti.
            """
            from collections import defaultdict
            from decimal import Decimal

            qs = models.OrderItem.objects\
                .filter(order__in=_orders())\
                .filter(Q(ticket__fare__ticket_type='conference')|Q(ticket=None))\
                .order_by('order')\
                .values_list('ticket__fare__code', 'ticket__fare__name', 'price', 'order')

            def _calc_prices(order_id, items):
                """
                Elimina gli item degli sconti e riduce in maniera proporzionale
                il valore dei restanti.
                """
                prices = set()
                discount = Decimal('0')
                total = Decimal('0')
                for item in items:
                    if item['price'] > 0:
                        prices.add(item['price'])
                        total += item['price']
                    else:
                        discount += item['price'] * -1

                for ix, item in reversed(list(enumerate(items))):
                    if item['price'] > 0:
                        item['price'] = item['price'] * (total - discount) / total
                    else:
                        del rows[ix]

            grouped = defaultdict(list)
            for fcode, fname, price, oid in qs:
                grouped[oid].append({
                    'code': fcode,
                    'name': fname,
                    'price': price,
                })
            for oid, items in grouped.items():
                _calc_prices(oid, items)

            # dopo l'utilizzo di _calc_prices ottengo dei prezzi che non trovo
            # più tra le tariffe ordinarie, raggruppo gli OrderItem risultanti
            # per codice tariffa e nuovo prezzo
            tcp = {}
            for rows in grouped.values():
                for item in rows:
                    code = item['code']
                    if code not in tcp:
                        tcp[code] = {
                            'code': code,
                            'name': item['name'],
                            'prices': {}
                        }
                    price = item['price']
                    if price not in tcp[code]['prices']:
                        tcp[code]['prices'][price] = { 'price': price, 'count': 0 }
                    tcp[code]['prices'][price]['count'] += 1
            return tcp.values()

        output = []
        for f in (
            _orders,
            _tickets,
            _order_items_by_ticket,
            _order_items_by_recipient,
            _order_items_by_fare,
            _recalculated_ticket_prices):
            if hasattr(f, 'short_description'):
                name = f.short_description
            else:
                name = f.__name__.replace('_', ' ').strip()
            output.append((name, f.__doc__, f()))
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
        url = urlresolvers.reverse('admin:assopy_user_change', args=(o.user.id,))
        return '<a href="%s">%s</a> (<a href="mailto:%s">email</a>)' % (url, o.user.name(), o.user.user.email)
    _user.short_description = 'user'
    _user.allow_tags = True

    def _valid(self, o):
        return o.valid(o.user)
    _valid.short_description = 'valid (maybe not used?)'
    _valid.boolean = True

admin.site.register(models.Coupon, CouponAdmin)

class UserOAuthInfoAdmin(admin.TabularInline):
    model = models.UserOAuthInfo

class UserAdmin(admin.ModelAdmin):
    list_display = ('_name', '_email', 'phone', 'address', '_identities', '_login')
    list_select_related = True
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'address',)

    inlines = (
        UserOAuthInfoAdmin,
    )

    def _name(self, o):
        return o.name()
    _name.short_description = 'name'
    _name.admin_order_field = 'user__first_name'

    def _email(self, o):
        return o.user.email
    _email.short_description = 'email'
    _email.admin_order_field = 'user__email'

    def _login(self, o):
        url = urlresolvers.reverse('admin:assopy-login-user', kwargs={'uid': o.id})
        return '<a href="%s">use this user</a>' % (url,)
    _login.short_description = 'login as this user'
    _login.allow_tags = True

    def _identities(self, o):
        return ','.join(i['provider'] for i in o.identities.values('provider'))
    _identities.short_description = '#id'

    def get_urls(self):
        urls = super(UserAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^(?P<uid>\d+)/login/$', self.admin_site.admin_view(self.login_as_user), name='assopy-login-user'),
            url(r'^(?P<uid>\d+)/order/$', self.admin_site.admin_view(self.new_order), name='assopy-user-order'),
            url(r'^resurrect/$', self.resurrect_user, name='assopy-resurrect-user'),
        )
        return my_urls + urls

    def login_as_user(self, request, uid):
        udata = (request.user.id, '%s %s' % (request.user.first_name, request.user.last_name),)
        user = get_object_or_404(models.User, pk=uid)
        from django.contrib import auth 
        auth.logout(request)
        user = auth.authenticate(uid=user.user.id)
        auth.login(request, user)
        request.session['resurrect_user'] = udata
        return http.HttpResponseRedirect(urlresolvers.reverse('assopy-tickets'))

    def resurrect_user(self, request):
        uid = request.session['resurrect_user'][0]
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

        user = get_object_or_404(models.User, pk=uid)

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
                return redirect('admin:assopy_user_change', user.id,)
        else:
            form = FormTickets()
        ctx = {
            'user': user,
            'form': form,
        }
        return render_to_response('admin/assopy/user/new_order.html', ctx, context_instance=template.RequestContext(request))
admin.site.register(models.User, UserAdmin)

class RefundAdminForm(forms.ModelForm):
    class Meta:
        model = models.Refund
        exclude = ('orderitem', 'done',)

class RefundAdmin(admin.ModelAdmin):
    list_display = ('_user', 'reason', '_description', '_price', 'created', 'status', 'done')
    form = RefundAdminForm

    def queryset(self, request):
        qs = super(RefundAdmin, self).queryset(request)
        qs = qs.select_related('orderitem__order__user__user')
        return qs

    def _user(self, o):
        return o.orderitem.order.user.name()
    _user.admin_order_field = 'orderitem__order__user__user__first_name'

    def _description(self, o):
        return o.orderitem.description
    _description.admin_order_field = 'orderitem__description'

    def _price(self, o):
        return o.orderitem.price

admin.site.register(models.Refund, RefundAdmin)
