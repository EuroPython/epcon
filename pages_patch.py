# -*- coding: UTF-8 -*-
import pages.utils
from pages import settings
from django.db import models, connection
from django.http import HttpResponseRedirect

def get_page_ids_by_slug(slug, parents=None):
    """
    Return all the page id according to a slug
    """
    if not parents:
        sql = '''
        SELECT c.page_id, c.language, MAX(c.creation_date)
        FROM pages_content c
        WHERE c.type = 'slug' AND c.body = %s
        GROUP BY c.page_id, c.language
        '''
    else:
        sql = '''
        SELECT c.page_id, c.language, MAX(c.creation_date)
        FROM pages_content c INNER JOIN pages_page p
            ON c.page_id = p.id
        WHERE c.type = 'slug' AND c.body = %%s AND p.parent_id in (%s)
        GROUP BY c.page_id, c.language
        '''
        sql = sql % ','.join(map(str, parents))
        
    cursor = connection.cursor()
    cursor.execute(sql, (slug, ))
    return [(c[0], c[1]) for c in cursor.fetchall()]

def patched_get_page_from_slug(slug, request, lang=None):
    from pages.models import Content, Page
    from django.core.urlresolvers import reverse
    relative_url = request.path.replace(reverse('pages-root'), '', 1)
    slugs = filter(None, relative_url.split('/'))
    lang = request.LANGUAGE_CODE
    parents = []
    for slug in slugs:
        page_ids = get_page_ids_by_slug(slug, parents)
        parents = map(lambda x: x[0], page_ids)
    if page_ids:
        page = Page.objects.get(id = page_ids[0][0])
        if len(page_ids) == 1 and page_ids[0][1] != lang:
            url = reverse('pages-root') + page.get_url(lang)
            if url != request.path:
                return url
        return page
    else:
        return None

from pages.models import Page, Content
from pages.utils import auto_render#, get_language_from_request, get_page_from_slug

def details(request, slug=None, lang=None):
    """
    Example view that get the root pages for navigation,
    and the current page if there is any root page.
    All is rendered with the current page's template.
    """
    pages = Page.objects.navigation().order_by("tree_id")
    current_page = False

    if pages:
        if slug:
            current_page = patched_get_page_from_slug(slug, request, lang)
        else:
            current_page = pages[0]

    if not current_page:
        raise Http404
    elif isinstance(current_page, basestring):
        return HttpResponseRedirect(current_page)

    if not current_page.calculated_status in (Page.PUBLISHED, Page.HIDDEN):
        raise Http404

    if not lang:
        lang = request.LANGUAGE_CODE #get_language_from_request(request, current_page)

    template_name = current_page.get_template()
    return template_name, locals()
details = auto_render(details)

