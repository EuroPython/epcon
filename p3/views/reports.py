# -*- coding: UTF-8 -*-
from conference import models as cmodels
from collections import defaultdict
from django import http
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from p3 import models
import mimetypes
import os.path

def secure_media(request, path):
    if not (request.user.is_superuser or request.user.groups.filter(name__in=('sim_report', 'hotel_report')).exists()):
        fname = os.path.splitext(os.path.basename(path))[0]
        if fname.rsplit('-', 1)[0] != request.user.username:
            return http.HttpResponseForbidden()
    fpath = settings.SECURE_STORAGE.path(path)
    guessed = mimetypes.guess_type(fpath)
    try:
        r = http.HttpResponse(file(fpath), mimetype=guessed[0])
        r['Content-Length'] = os.path.getsize(fpath)
        if guessed[1]:
            r['Content-Encoding'] = guessed[1]
        return r
    except IOError, e:
        if e.errno == 2:
            raise http.Http404()
        else:
            raise

@login_required
def sim_report(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='sim_report').exists()):
        return http.HttpResponseForbidden()
    tickets = cmodels.Ticket.objects.filter(
        orderitem__order___complete=True,
        fare__in=cmodels.Fare.objects.filter(
            code__startswith='SIM', conference=settings.CONFERENCE_CONFERENCE),
    ).order_by('orderitem__order').select_related('p3_conference_sim')
    if request.method == 'POST':
        t = tickets.get(id=request.POST['ticket'])
        t.frozen = not t.frozen
        t.save()

    compiled = dict([ (x[0], { 'label': x[1], 'total': 0, 'done': 0 }) for x in models.TICKET_SIM_TYPE ])
    for t in tickets:
        if t.p3_conference_sim and t.p3_conference_sim.document:
            sim_type = t.p3_conference_sim.sim_type
            compiled[sim_type]['total'] += 1
            if t.frozen:
                compiled[sim_type]['done'] += 1
    ctx = {
        'tickets': tickets,
        'compiled': compiled,
    }
    return render(request, 'p3/sim_report.html', ctx)

@login_required
def hotel_report(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='hotel_report').exists()):
        return http.HttpResponseForbidden()
    tickets = models.TicketRoom.objects\
        .valid_tickets()\
        .select_related('ticket__fare', 'ticket__orderitem')\
        .order_by('ticket__orderitem__order')
    if request.method == 'POST':
        t = tickets.get(id=request.POST['ticket'])
        t.frozen = not t.frozen
        t.save()
    grouped = {
        'rooms': {},
        'beds': {},
    }
    omap = defaultdict(lambda: 0)
    for t in tickets:
        fcode = t.ticket.fare.code
        if fcode[2] == '1':
            key = '0single'
        elif fcode[2] == '2':
            key = '1double'
        elif fcode[2] == '3':
            key = '2triple'
        elif fcode[2] == '4':
            key = '3quadruple'
        if fcode[1] == 'R':
            g = grouped['rooms']
            if key not in g:
                g[key] = {}

            # oid/order_key servono solo a raggruppare graficamente i biglietti
            # per la stessa camera
            oid = '%s:%s' % (t.ticket.orderitem.order_id, fcode)
            order_key = oid + ('_%d' % (omap[oid] / int(fcode[2])))
            omap[oid] += 1
            if order_key not in g[key]:
                g[key][order_key] = []
            g[key][order_key].append(t)
        else:
            g = grouped['beds']
            if key not in g:
                g[key] = {}
            period = (t.checkin, t.checkout)
            if period not in g[key]:
                g[key][period] = []
            g[key][period].append(t)

    rooms = []
    for type, orders in sorted(grouped['rooms'].items()):
        rooms.append((type[1:], sorted(orders.items(), key=lambda x: (x[1][0].checkin, x[1][0].ticket.name))))

    beds = []
    for type, periods in sorted(grouped['beds'].items()):
        beds.append((type[1:], sorted(periods.items(), key=lambda x: x[0][0])))
    ctx = {
        'rooms': rooms,
        'beds': beds,
    }
    return render(request, 'p3/hotel_report.html', ctx)
