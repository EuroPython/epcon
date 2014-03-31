# -*- coding: UTF-8 -*-
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
