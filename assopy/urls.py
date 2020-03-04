from django.conf.urls import url as re_path

from assopy import views


urlpatterns = [
    # Views below continue to be used as of EP2019/2020
    re_path(
        r"orders/(?P<order_code>.+)/invoices/(?P<code>.+).html$",
        views.invoice,
        name="assopy-invoice-html",
        kwargs={"mode": "html"},
    ),
    re_path(
        r"orders/(?P<order_code>.+)/invoices/(?P<code>.+).pdf$",
        views.invoice,
        name="assopy-invoice-pdf",
        kwargs={"mode": "pdf"},
    ),
]

