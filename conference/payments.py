
import stripe

from django.conf import settings

from conference.models import StripePayment


STRIPE_PAYMENTS_CURRENCY = "eur"


class PaymentError(Exception):
    pass


def charge_for_payment(stripe_payment):
    assert isinstance(stripe_payment, StripePayment)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        charge = stripe.Charge.create(
            amount=stripe_payment.amount_for_stripe(),
            currency=STRIPE_PAYMENTS_CURRENCY,
            card=stripe_payment.token,
            description=stripe_payment.description,
            idempotency_key=stripe_payment.uuid,
            metadata={
                'order_code': stripe_payment.order.code,
                'order_uuid': stripe_payment.order.uuid,
                'stripe_payment_uuid': stripe_payment.uuid
            }
        )
        stripe_payment.charge_id = charge.id
        stripe_payment.status = stripe_payment.STATUS_CHOICES.SUCCESSFUL
        stripe_payment.save()

    except stripe.error.StripeError as e:
        stripe_error = e.json_body['error']
        stripe_payment.status = stripe_payment.STATUS_CHOICES.FAILED
        stripe_payment.message = (
            f"{stripe_error['type']} -- {stripe_error['message']}"
        )
        stripe_payment.save()

        raise PaymentError(stripe_error)
