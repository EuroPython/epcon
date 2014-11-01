# -*- coding: utf-8 -*-
from cms.api import add_plugin
from cms.models import Page as CMSPage, Title
from pages.models import Page as PagesPage


def copy_pages():

    pages = PagesPage.objects.order_by('tree_id', 'lft', )
    # remove all the previous pages
    CMSPage.objects.all().delete()

    parents = {}

    for page in pages:
        cmspage = CMSPage()
        # replicate the language independent structure information
        # thanks to the common ancestor we can reuse exactly the same tree
        # information
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
        # replicate the language dependent data
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
                if content.type in ('subtitle', 'text', 'right-column'):
                    placeholder = cmspage.placeholders.get(slot=content.type)
                    # For the main placeholders we need to scan whether content
                    # is markdown or plain HTML
                    # This is a very naif check, but does the trick in this
                    # context
                    if content.body.find('<p>') > -1:
                        add_plugin(placeholder, plugin_type='TextPlugin', language=language, body=content.body)
                    else:
                        add_plugin(placeholder, plugin_type='MarkItUpPlugin', language=language, body=content.body)
                elif content.type not in ('slug', 'title'):
                    # Fallback import
                    placeholder = cmspage.placeholders.get(slot=content.type)
                    add_plugin(placeholder, plugin_type='TextPlugin', language=language, body=content.body)