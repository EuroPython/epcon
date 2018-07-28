# -*- coding: UTF-8 -*-
from assopy import models
from conference import models as cmodels
from collections import defaultdict
from decimal import Decimal

def _orders(**kw):
    qs = models.Order.objects.filter(_complete=True)
    if 'year' in kw:
        qs = qs.filter(created__year=kw['year'])
    if 'from' in kw:
        qs = qs.filter(created__gte=kw['from'])
    if 'to' in kw:
        qs = qs.filter(created__lt=kw['to'])
    return qs

def movimento_cassa(**kw):
    """
    Elenca i movimenti di cassa in/out nel periodo specificato. Tramite **kw si
    può specificare

        - year
        - from (data inizio)
        - to (data fine)

    Il dizionario in output ha tre chiavi:
        - in
        - out
            sono i movimenti in ingresso/uscita, nella forma:
                codice biglietto|discount -> quantità, totale
        - error
            sono gli ordini con righe d'ordine incongruenti, senza un biglietto
            ma con importo maggiore di zero.
    """
    items = models.OrderItem.objects\
        .filter(order__in=_orders(**kw))\
        .values('code', 'ticket', 'price', 'order__code')
    fares = dict(cmodels.Fare.objects\
        .values_list('code', 'description'))
    output = {
        'in': defaultdict(lambda: [0, 0]),
        'out': defaultdict(lambda: [0, 0]),
        'errors': defaultdict(lambda: [0, 0]),
    }
    for row in items:
        if row['price'] < 0:
            if row['code'].startswith('_'):
                k = output['out'][(row['code'], fares.get(row['code']))]
            else:
                k = output['out'][('OTHER', '')]
        elif not row['ticket']:
            k = output['errors'][(row['order__code'], '')]
        else:
            k = output['in'][(row['code'], fares.get(row['code']))]
        k[0] += 1
        k[1] += row['price']

    totals = {
        'in': 0,
        'out': 0,
        'errors': 0,
    }
    for k, v in output.items():
        data = sorted(v.items())
        output[k] = data
        totals[k] = sum([x[1][1] for x in data])

    output['totals'] = totals

    return output

movimento_cassa.description = "Elenco dei movimenti di cassa"
movimento_cassa.template = '''
<table>
    <tr>
        <th>Code</th>
        <th>Qty</th>
        <th style="width: 70px;">Price</th>
    </tr>
    {% for code, row in data.in %}
    <tr>
        <td title="{{ code.1 }}">{{ code.0 }}</td>
        <td>{{ row.0 }}</td>
        <td style="text-align: right;">€ {{ row.1|floatformat:"2" }}</td>
    </tr>
    {% endfor %}
    <tr>
        <th colspan="2">Total</th>
        <td style="text-align: right;">€ {{ data.totals.in }}</td>
    </tr>
    {% for code, row in data.out %}
    <tr>
        <td title="{{ code.1 }}">{{ code.0 }}</td>
        <td>{{ row.0 }}</td>
        <td style="text-align: right; color: red;">€ {{ row.1|floatformat:"2" }}</td>
    </tr>
    {% endfor %}
    <tr>
        <th colspan="2">Total</th>
        <td style="text-align: right;">€ {{ data.totals.out }}</td>
    </tr>
</table>
{% if data.errors %}
<h3>Errors</h3>
<table>
    <tr>
        <td>Order</th>
        <th style="width: 70px;">Price</th>
    </tr>
    {% for code, row in data.errors %}
    <tr>
        <td>{{ code.0 }}</th>
        <td style="text-align: right;">€ {{ row.1|floatformat:"2" }}</th>
    </tr>
    {% endfor %}
    <tr>
        <th>Total</th>
        <td style="text-align: right;">€ {{ data.totals.errors }}</td>
    </tr>
</table>
{% endif %}
'''

def prezzo_biglietti_ricalcolato(**kw):
    """
    Ricalcola il ricavo dei biglietti eliminando quelli gratuiti e
    ridistribuendo il prezzo sui rimanenti.
    """
    # mi interessano solo gli ordini che riguardano acquisti di biglietti
    # "conferenza"
    orders = models.Order.objects\
        .filter(id__in=_orders(**kw), orderitem__ticket__fare__ticket_type='conference')\
        .values('id')\
        .distinct()
    qs = models.OrderItem.objects\
        .filter(order__in=orders)\
        .values_list('ticket__fare__code', 'ticket__fare__name', 'price', 'order')

    fares = set(cmodels.Fare.objects\
        .filter(ticket_type='conference')\
        .values_list('code', flat=True))

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
                del items[ix]

    grouped = defaultdict(list)
    for fcode, fname, price, oid in qs:
        if fcode in fares or price < 0:
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
    # Replace prices dicts with sorted lists
    for code in tcp.keys():
        prices_list = [entry
                       for price, entry in sorted(tcp[code]['prices'].items(),
                                                  reverse=True)]
        tcp[code]['prices'] = prices_list
    # Create list sorted by fare code
    ticket_sales = [entry for code, entry in sorted(tcp.items())]
    return ticket_sales
prezzo_biglietti_ricalcolato.template = '''
<table>
    <tr>
        <th>Code</th>
        <th>Qty</th>
        <th style="width: 70px;">Price</th>
    </tr>
    {% for ticket in data %}
        {% for p in ticket.prices %}
        <tr>
            {% if forloop.counter == 1 %}
            <td title="{{ ticket.name }}" rowspan="{{ ticket.prices|length }}">{{ ticket.code }}</td>
            {% endif %}
            <td>{{ p.count }}</td>
            <td>€ {{ p.price|floatformat:"2" }}</td>
        </tr>
        {% endfor %}
    {% endfor %}
</table>
'''
