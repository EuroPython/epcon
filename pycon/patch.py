# -*- coding: UTF-8 -*-
def patch_pages():
    from django import http
    from django.conf import settings
    from pages import managers
    from pages import models

    class MyPageManager(managers.PageManager):
        def from_path(self, complete_path, lang, exclude_drafts=True):
            output = super(MyPageManager, self).from_path(complete_path, lang, exclude_drafts)
            if output is None:
                # non esiste una pagina per il path richiesto nella lingua
                # specificata, ma forse esiste in un'altra lingua...
                for alternative_lang, _ in settings.PAGE_LANGUAGES:
                    if alternative_lang != lang:
                        alt_content = super(MyPageManager, self).from_path(complete_path, alternative_lang, exclude_drafts)
                        if alt_content:
                            # ho trovato una pagina che coincide con
                            # `complete_path` ma nella lingua `alternative_lang`,
                            # faccio un redirect...
                            from pycon.middleware import RisingResponse
                            RisingResponse.stop(http.HttpResponseRedirect(alt_content.get_url_path(lang)))
            return output

    models.Page.add_to_class('objects', MyPageManager())

    from pages import views as pviews
    # Questa view reimplementa il vecchio supporto di pages per le richieste ajax.
    # Se una richiesta è ajax viene utilizzato un template ad hoc
    class DetailsWithAjaxSupport(pviews.Details):
        def get_template(self, request, context):
            tpl = super(DetailsWithAjaxSupport, self).get_template(request, context)
            if request.is_ajax():
                import os.path
                bname, fname = os.path.split(tpl)
                tpl = os.path.join(bname, 'body_' + fname)
            return tpl
    pviews.details = DetailsWithAjaxSupport()
