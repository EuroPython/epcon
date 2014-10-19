# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from cms.api import add_plugin
from cms.models import Page as CMSPage, Title
from pages.models import Page as PagesPage


def copy_pages():

    pages = PagesPage.objects.order_by('tree_id', 'lft', )
    CMSPage.objects.all().delete()

    parents = {}

    for page in pages:
        cmspage = CMSPage()
        cmspage.pk = page.pk
        cmspage.creation_date = page.creation_date
        cmspage.publication_date = page.publication_date
        cmspage.publication_end_date = page.publication_end_date
        cmspage.changed_date = page.last_modification_date
        cmspage.template = 'django_' + page.template
        cmspage.level = page.level
        cmspage.lft = page.lft
        cmspage.rght = page.rght
        cmspage.tree_id = page.tree_id
        cmspage.site_id = 1
        if page.parent_id in parents:
            cmspage.parent = parents[page.parent_id]
        cmspage.save(no_signals=True)
        cmspage.rescan_placeholders()
        parents[cmspage.pk] = cmspage
        for language in page.get_languages():
            cmstitle = Title()
            cmstitle.language = language
            cmstitle.title = page.title(language)
            cmstitle.slug = page.slug(language)
            cmstitle.page = cmspage
            cmstitle.update_path()
            cmstitle.save()
            contents = page.content_by_language(language)
            for content in contents:
                if content.type not in ('slug', 'title'):
                    print(content.type, cmspage.template)
                    placeholder = cmspage.placeholders.get(slot=content.type)
                    print(placeholder)
                    add_plugin(placeholder, plugin_type='TextPlugin', language=language, body=content.body)