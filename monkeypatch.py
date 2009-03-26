# -*- coding: UTF-8 -*-
import pages.utils

def patched_get_page_from_slug(slug, request, lang=None):
    from pages.models import Content, Page
    from django.core.urlresolvers import reverse
    lang = pages.utils.get_language_from_request(request)
    relative_url = request.path.replace(reverse('pages-root'), '')
    page_ids = Content.objects.get_page_ids_by_slug(slug)
    pages_list = Page.objects.filter(id__in=page_ids)
    current_page = None
    for page in pages_list:
        if page.get_url(lang) == relative_url:
            return page
    return None

pages.utils.get_page_from_slug = patched_get_page_from_slug
