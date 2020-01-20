from django.conf.urls import url

from assopy import views


urlpatterns = [
    # Views below continue to be used as of EP2019/2020
    url(
        r"orders/(?P<order_code>.+)/invoices/(?P<code>.+).html$",
        views.invoice,
        name="assopy-invoice-html",
        kwargs={"mode": "html"},
    ),
    url(
        r"orders/(?P<order_code>.+)/invoices/(?P<code>.+).pdf$",
        views.invoice,
        name="assopy-invoice-pdf",
        kwargs={"mode": "pdf"},
    ),
]

