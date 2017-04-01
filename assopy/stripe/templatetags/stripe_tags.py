from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf import settings
from django import template

register = template.Library()


@register.inclusion_tag("assopy/stripe/checkout_script.html")
def stripe_checkout_script(order, company_name=None, company_logo=None):
    """
    Template tag that renders the stripe checkout script.
    See https://stripe.com/docs/tutorials/checkout for more info.
    """
    company_name = company_name or settings.STRIPE_COMPANY_NAME
    company_logo = company_logo or settings.STRIPE_COMPANY_LOGO

    # stripe need the amount in cents
    total_amount = order.total() * 100

    # order description
    description = "\n".join(order.orderitem_set.values_list("description", flat=True))

    return {
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "company_name": company_name,
        "company_logo": company_logo,
        "amount": total_amount,
        "description": description,
        "currency": settings.STRIPE_CURRENCY,
        "allow_remember_me": settings.STRIPE_ALLOW_REMEMBER_ME,
        "user_email": order.user.user.email,
    }


@register.inclusion_tag("assopy/stripe/checkout_form.html")
def stripe_checkout_form(order, company_name=None, company_logo=None):
    """
    Template tag that renders a ready-to-use stripe checkout form.
    See https://stripe.com/docs/tutorials/checkout for more info.
    """
    return {
        "order": order,
        "company_name": company_name or settings.STRIPE_COMPANY_NAME,
        "company_logo": company_logo or settings.STRIPE_COMPANY_LOGO,
    }
