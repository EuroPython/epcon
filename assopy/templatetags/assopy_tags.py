from django import template
from django.core import paginator

import urllib.request, urllib.parse, urllib.error

register = template.Library()


@register.simple_tag(takes_context=True)
def paginate(context, qs, count=20):
    pages = paginator.Paginator(qs, int(count))
    try:
        ix = int(context['request'].GET.get('page', 1))
    except ValueError:
        ix = 1
    try:
        return pages.page(ix)
    except:
        ix = 1 if ix < 1 else pages.num_pages
        return pages.page(ix)


@register.simple_tag(takes_context=True)
def add_page_number_to_query(context, page, get=None):
    if get is None:
        get = context['request'].GET.copy()
    else:
        get = dict(get)
    get['page'] = page
    return urllib.parse.urlencode(get)
