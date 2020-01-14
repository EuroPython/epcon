from django.conf.urls import url

from assopy import views


urlpatterns = [
    # Manage user profile
    url(r"^profile/$", views.profile, name="assopy-profile"),
    url(r"^billing/$", views.billing, name="assopy-billing"),
    url(r"^checkout/$", views.checkout, name="assopy-checkout"),
    url(r"^tickets/$", views.tickets, name="assopy-tickets"),
    url(
        r"orders/(?P<assopy_id>.+)/completed$",
        views.order_complete,
        name="assopy-order-complete",
    ),

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

