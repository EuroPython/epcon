from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

class AssopyApphook(CMSApp):
    name = _("Assopy")
    urls = ["assopy.urls"]

class ConferenceApphook(CMSApp):
    name = _("Conference")
    urls = ["conference.urls"]

class P3Apphook(CMSApp):
    name = _("P3")
    urls = ["p3.urls"]

class BlogApphook(CMSApp):
    name = _("Blog")
    urls = ["microblog.urls"]


apphook_pool.register(AssopyApphook)
apphook_pool.register(ConferenceApphook)
apphook_pool.register(P3Apphook)
apphook_pool.register(BlogApphook)
