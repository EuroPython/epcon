# -*- coding: UTF-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext

def map_js(request):
    return render_to_response(
        'p3/map.js', {}, context_instance=RequestContext(request), mimetype = 'text/javascript')
