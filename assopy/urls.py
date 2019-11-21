from django.conf import settings as dsettings
from django.conf.urls import url, include

from assopy import views


urlpatterns = [
    # Manage user profile
    url(r"^profile/$", views.profile, name="assopy-profile"),
    url(
        r"^profile/identities$",
        views.profile_identities,
        name="assopy-profile-identities",
    ),
    url(r"^billing/$", views.billing, name="assopy-billing"),
    url(r"^checkout/$", views.checkout, name="assopy-checkout"),
    url(r"^tickets/$", views.tickets, name="assopy-tickets"),
    url(
        r"orders/(?P<order_id>\d+)/(?P<item_id>\d+)/voucher$",
        views.voucher,
        name="assopy-orderitem-voucher",
    ),
    url(
        r"orders/(?P<order_id>\d+)/(?P<item_id>\d+)/refund$",
        views.refund,
        name="assopy-orderitem-refund",
    ),
    url(
        r"orders/(?P<assopy_id>.+)/completed$",
        views.order_complete,
        name="assopy-order-complete",
    ),
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
    url(
        r"orders/(?P<order_code>.+)/credit-note/(?P<code>.+).html$",
        views.credit_note,
        name="assopy-credit_note-html",
        kwargs={"mode": "html"},
    ),
    url(
        r"orders/(?P<order_code>.+)/credit-note/(?P<code>.+).pdf$",
        views.credit_note,
        name="assopy-credit_note-pdf",
        kwargs={"mode": "pdf"},
    ),
]

if "assopy.stripe" in dsettings.INSTALLED_APPS:
    urlpatterns += [url(r"^stripe/", include("assopy.stripe.urls"))]
