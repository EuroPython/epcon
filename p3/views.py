# -*- coding: UTF-8 -*-

from pages.views import details
def root(request):
    return details(request)
