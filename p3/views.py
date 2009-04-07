# -*- coding: UTF-8 -*-

from pages.views import details
from django.shortcuts import render_to_response
from django.template import RequestContext

def root(request):
    return details(request)

def gmap(request):
    return render_to_response(
        'p3/gmap.js',{}, context_instance = RequestContext(request), mimetype = 'text/javascript')
