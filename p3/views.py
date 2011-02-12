# -*- coding: UTF-8 -*-
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from assopy.views import render_to, HttpResponseRedirectSeeOther

import forms
import models
from conference.models import Attendee

def map_js(request):
    return render_to_response(
        'p3/map.js', {}, context_instance=RequestContext(request), mimetype = 'text/javascript')

@login_required
@render_to('p3/tickets.html')
def tickets(request):
    tickets = request.user.attendee_set.conference(settings.CONFERENCE_CONFERENCE)
    return {
        'attendee_tickets': tickets,
    }

@login_required
@transaction.commit_on_success
def ticket(request, tid):
    a = get_object_or_404(Attendee, user=request.user, pk=tid)
    if request.method == 'POST':
        if a.ticket.type == 'conference':
            try:
                p3c = a.p3_conference
            except models.AttendeeProfile.DoesNotExist:
                p3c = None
        form = forms.FormAttendee(instance=p3c, data=request.POST)
        if not form.is_valid():
            return http.HttpResponseBadRequest()
        data = form.cleaned_data
        a.name = data['attendee_name']
        a.save()
        x = form.save(commit=False)
        x.attendee = a
        x.save()
    return HttpResponseRedirectSeeOther(reverse('p3-tickets'))
