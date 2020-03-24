import csv
from io import StringIO

from django import forms
from django import http
from django.conf import settings
from django.contrib import admin, auth, messages
from django.contrib.admin.utils import quote
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse, re_path
from django.shortcuts import get_object_or_404, redirect
from django.template import Template, Context
from django.template.response import TemplateResponse

from assopy import dataaccess as assopy_dataaccess
from assopy import forms as assopy_forms
from assopy import models, stats
from conference.accounts import send_verification_email
from conference.invoicing import render_invoice_as_html
from conference.models import Conference, Fare, StripePayment


class CountryAdmin(admin.ModelAdmin):
    list_display = ('printable_name', 'vat_company', 'vat_company_verify', 'vat_person')
    list_editable = ('vat_company', 'vat_company_verify', 'vat_person')
    search_fields = ('name', 'printable_name', 'iso', 'numcode')


class OrderItemInlineAdmin(admin.TabularInline):
    model = models.OrderItem
    raw_id_fields = ('ticket',)
    extra = 0
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


class StripePaymentInlineFormset(forms.models.BaseInlineFormSet):
    def save_new(self, form, commit=True):
        payment = super().save_new(form, commit=False)
        # Order has a relation to assopy user, payment to django user
        payment.user = self.order.user.user

        if commit:
            payment.save()

        return payment

class StripePaymentInline(admin.TabularInline):
    formset = StripePaymentInlineFormset
    model = StripePayment
    extra = 0
    can_delete = False
    fields = ('status', 'created', 'modified', 'charge_id', 'amount', 'uuid')

    def get_readonly_fields(self, request, obj=None):
        return ['created', 'modified', 'uuid']

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.order = obj
        return formset


class OrderAdminForm(forms.ModelForm):
    method = forms.ChoiceField(choices=(
        *models.ORDER_PAYMENT,
        ('admin', 'Admin'),
    ))

    class Meta:
        model = models.Order
        exclude = ('method',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = models.AssopyUser.objects.all().select_related('user')
        if self.initial:
            self.fields['method'].initial = self.instance.method

    def clean_assopy_id(self):
        aid = self.cleaned_data.get('assopy_id')
        if aid == '':
            aid = None
        return aid

    def save(self, *args, **kwargs):
        self.instance.method = self.cleaned_data['method']
        return super().save(*args, **kwargs)


class DiscountListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'discounts'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'discounts'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'With discounts'),
            ('no', 'Regular order'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(orderitem__price__lt=0)
        elif self.value() == 'no':
            return queryset.exclude(orderitem__price__lt=0)


class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'code', '_user', '_email',
        '_created', 'method',
        '_items', '_complete', '_invoice',
        '_total_nodiscount', '_discount', '_total_payed', 'country',
    )
    list_select_related = True
    list_filter = ('method', '_complete', DiscountListFilter, 'country')
    raw_id_fields = ('user',)
    search_fields = (
        'code', 'card_name',
        'user__user__first_name', 'user__user__last_name', 'user__user__email',
        'billing_notes',
    )
    readonly_fields = ['payment_date', 'stripe_charge_id']
    date_hierarchy = 'created'
    actions = ('do_edit_invoices',)

    form = OrderAdminForm

    inlines = (
        OrderItemInlineAdmin,
        StripePaymentInline,
    )

    def has_delete_permission(self, request, obj=None):
        # se ho emesso un invoice impedisco di cancellare l'ordine
        if obj and obj.invoices.exclude(payment_date=None).exists():
            return False
        else:
            return super().has_delete_permission(request, obj)

    def get_actions(self, request):
        # elimino l'action delete per costringere l'utente ad usare il pulsante
        # nella pagina di dettaglio. La differenza tra il pulsante e questa
        # azione che l'ultima non chiama la `.delete()` del modello.
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def _user(self, o):
        url = reverse('admin:auth_user_change', args=(o.user.user_id,))
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
    _total_payed.short_description = 'Paid'

    def _invoice(self, o):
        output = []
        # MAL: PDF generation is slower, so default to HTML
        if 1 or settings.DEBUG:
            vname = 'assopy-invoice-html'
        else:
            vname = 'assopy-invoice-pdf'
        for i in o.invoices.all():
            url = reverse(
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
        admin_view = self.admin_site.admin_view
        my_urls = [
            re_path(r'^invoices/$', admin_view(self.edit_invoices), name='assopy-edit-invoices'),
            re_path(r'^stats/$', admin_view(self.stats), name='assopy-order-stats'),
            re_path(
                r'^(?P<order_id>.+)/invoices/latest$',
                admin_view(self.latest_invoice),
                name='assopy-order-latest-invoice'
            ),
        ]
        return my_urls + urls

    def latest_invoice(self, request, order_id):
        invoice = models.Invoice.objects.filter(
            order__pk=order_id).order_by('emit_date').last()

        return redirect('admin:assopy_invoice_change', invoice.id)

    def do_edit_invoices(self, request, queryset):
        ids = [ str(o.id) for o in queryset ]
        if ids:
            url = reverse('admin:assopy-edit-invoices') + '?id=' + ','.join(ids)
            return redirect(url)
        else:
            self.message_user(request, 'no orders')
    do_edit_invoices.short_description = 'Edit/Make invoices'

    def edit_invoices(self, request):
        try:
            ids = [int(el) for el in request.GET['id'].split(',')]
        except KeyError:
            return http.HttpResponseBadRequest('orders id missing')
        except ValueError:
            return http.HttpResponseBadRequest('invalid id list')
        orders = models.Order.objects.filter(id__in=ids)
        if not orders.exists():
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
        return TemplateResponse(request, 'assopy/admin/edit_invoices.html', ctx)

    def stats_conference(self, conf):

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

        ctx = {
            'conferences': [],
        }
        for c in Conference.objects.order_by('-conference_start')[:3]:
            ctx['conferences'].append((c, self.stats_conference(c)))

        return TemplateResponse(request, 'assopy/admin/order_stats.html', ctx)


class CouponAdminForm(forms.ModelForm):
    class Meta:
        model = models.Coupon
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CouponAdminForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = models.AssopyUser.objects\
            .all()\
            .select_related('user')\
            .order_by('user__first_name', 'user__last_name')

        if self.instance:
            if self.instance.pk:
                self.fields['fares'].queryset = Fare.objects.filter(conference=self.instance.conference_id)
            else:
                self.fields['fares'].queryset = Fare.objects.filter(conference=settings.CONFERENCE_CONFERENCE)

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
        if 'conference__code__exact' not in request.GET:
            q = request.GET.copy()
            q['conference__code__exact'] = settings.CONFERENCE_CONFERENCE
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super(CouponAdmin,self).changelist_view(request, extra_context=extra_context)

    def _user(self, o):
        if not o.user:
            return ''
        url = reverse('admin:auth_user_change', args=(o.user.user_id,))
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


class AuthUserAdmin(UserAdmin):
    list_display = UserAdmin.list_display + ('_doppelganger',)

    def get_urls(self):
        f = self.admin_site.admin_view
        urls = [
            re_path(r'^(?P<uid>\d+)/login/$', f(self.create_doppelganger), name='auser-create-doppelganger'),
            re_path(r'^(?P<uid>\d+)/order/$', f(self.new_order), name='auser-order'),
            re_path(r'^(?P<uid>\d+)/send_verification_email$', f(self.send_verification_email), name='auser-send-verification-email'),
            re_path(r'^kill_doppelganger/$', self.kill_doppelganger, name='auser-kill-doppelganger'),
        ]
        return urls + super(AuthUserAdmin, self).get_urls()

    def create_doppelganger(self, request, uid):
        # user è l'utente corrente, quello che vuole creare un doppelganger.
        # salvo nella sessione del nuovo utente i dati che mi servono per
        # conoscere chi sta controllando il doppelganger.
        user = request.user
        udata = (user.id, '%s %s' % (user.first_name, user.last_name),)

        auth.logout(request)
        user = auth.authenticate(uid=uid)
        auth.login(request, user)
        request.session['doppelganger'] = udata

        return http.HttpResponseRedirect(reverse('user_panel:dashboard'))

    def kill_doppelganger(self, request):
        uid = request.session.pop('doppelganger')[0]

        auth.logout(request)
        user = auth.authenticate(uid=uid)
        if user.is_superuser:
            auth.login(request, user)
        return http.HttpResponseRedirect('/')

    def new_order(self, request, uid):
        user = get_object_or_404(models.AssopyUser, user=uid)

        class FormTickets(assopy_forms.FormTickets):
            coupon = forms.CharField(label='Coupon(s)', required=False)
            country = forms.CharField(max_length=2, required=False)
            address = forms.CharField(max_length=150, required=False)
            card_name = forms.CharField(max_length=200, required=True, initial=user.card_name or user.name())
            billing_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
            remote = forms.BooleanField(required=False, initial=True, help_text='debug only, fill the order on the remote backend')
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.fields['payment'].choices = (('admin', 'Admin'),) + tuple(self.fields['payment'].choices)
                self.fields['payment'].initial = 'admin'

            def available_fares(self):
                return Fare.objects.available(conference=settings.CONFERENCE_CONFERENCE)

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
                            output.append(models.Coupon.objects.get(conference=settings.CONFERENCE_CONFERENCE, code=c))
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
        return TemplateResponse(request, 'admin/auth/user/new_order.html', ctx)

    def _doppelganger(self, o):
        url = reverse('admin:auser-create-doppelganger', kwargs={'uid': o.id})
        return '<a href="%s" target="_blank">become this user</a>' % url
    _doppelganger.allow_tags = True
    _doppelganger.short_description = 'Doppelganger'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        ctx = extra_context or {}
        ctx['user_data'] = assopy_dataaccess.all_user_data(object_id)
        return super().change_view(request, object_id, form_url, ctx)

    def send_verification_email(self, request, uid):
        user = User.objects.get(pk=uid)

        if not user.is_active:
            send_verification_email(user, get_current_site(request))
            messages.add_message(request, messages.SUCCESS, 'Verification email sent successfully.')
        else:
            messages.add_message(request, messages.ERROR, 'This user is active!')

        return redirect ('.')


class InvoiceAdmin(admin.ModelAdmin):
    actions = ('do_csv_invoices',)
    list_display = ('__str__', '_invoice', '_user', 'payment_date', 'price', '_order', 'vat')
    date_hierarchy = 'payment_date'
    search_fields = (
        'code', 'order__code', 'order__card_name',
        'order__user__user__first_name', 'order__user__user__last_name', 'order__user__user__email',
        'order__billing_notes',)
    readonly_fields = ('price', 'vat', 'order')
    exclude = ('assopy_id',)

    def _order(self, o):
        order = o.order
        url = reverse('admin:assopy_order_change', args=(order.id,))
        return '<a href="%s">%s</a>' % (url, order.code)
    _order.allow_tags = True
    _order.admin_order_field = 'order'

    def _user(self, o):
        u = o.order.user.user
        name = '%s %s' % (u.first_name, u.last_name)
        admin_url = reverse('admin:auth_user_change', args=(u.id,))
        dopp_url = reverse('admin:auser-create-doppelganger', kwargs={'uid': u.id})
        html = '<a href="%s">%s</a> (<a href="%s">D</a>)' % (admin_url, name, dopp_url)
        if o.order.card_name != name:
            html += ' - ' + o.order.card_name
        return html
    _user.allow_tags = True
    _user.admin_order_field = 'order__user__user__first_name'

    def _invoice(self, i):
        fake = not i.payment_date
        view = reverse('assopy-invoice-html', kwargs={'order_code': i.order.code, 'code': i.code})
        download = reverse('assopy-invoice-pdf', kwargs={'order_code': i.order.code, 'code': i.code})
        return '<a href="%s">View</a> - <a href="%s">Download</a> %s' % (view, download, '[Not payed]' if fake else '')
    _invoice.allow_tags = True
    _invoice.short_description = 'Download'

    def has_delete_permission(self, request, obj=None):
        if obj and obj.payment_date != None:
            return False
        else:
            return super(InvoiceAdmin, self).has_delete_permission(request, obj)

    def do_csv_invoices(self, request, queryset):
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

    def get_urls(self):
        urls = super().get_urls()
        admin_view = self.admin_site.admin_view
        my_urls = [
            re_path(
                r'^(?P<invoice_id>.+)/regenerate$',
                admin_view(self.regenerate_invoice),
                name='assopy-invoice-regenerate'
            ),
            re_path(
                r'^(?P<invoice_id>.+)/order',
                admin_view(self.associated_order),
                name='assopy-invoice-associated-order'
            ),
            re_path(
                r'^(?P<invoice_id>.+)/preview',
                admin_view(self.preview),
                name='assopy-invoice-preview'
            ),
        ]
        return my_urls + urls

    def regenerate_invoice(self, request, invoice_id):
        invoice = models.Invoice.objects.get(pk=invoice_id)

        invoice.html = render_invoice_as_html(invoice)
        invoice.save()

        messages.add_message(request, messages.SUCCESS, 'Invoice regenerated successfully.')
        return redirect ('.')

    def associated_order(self, request, invoice_id):
        invoice = models.Invoice.objects.get(pk=invoice_id)

        return redirect('admin:assopy_order_change', invoice.order.id)

    def preview(self, request, invoice_id):
        invoice = models.Invoice.objects.get(pk=invoice_id)

        return redirect('assopy-invoice-html', order_code=invoice.order.code, code=invoice.code)


class InvoiceLogAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'order', 'invoice','date'
    )


admin.site.unregister(User)
admin.site.register(User, AuthUserAdmin)

admin.site.register(models.Country, CountryAdmin)
admin.site.register(models.Coupon, CouponAdmin)
admin.site.register(models.Invoice, InvoiceAdmin)
admin.site.register(models.InvoiceLog, InvoiceLogAdmin)
admin.site.register(models.Order, OrderAdmin)
admin.site.register(models.Vat)
