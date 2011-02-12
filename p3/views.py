# -*- coding: UTF-8 -*-
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext

from assopy.views import render_to

import models

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
