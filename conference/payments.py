
import stripe
import uuid

from django.conf import settings
from django.core.urlresolvers import reverse

from conference.models import StripePayment


STRIPE_PAYMENTS_CURRENCY = "eur"


class PaymentError(Exception):
    pass


def prepare_for_payment(request, order, description):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        stripe_payment = StripePayment.objects.create(
            order=order,
            user=request.user,
            uuid=str(uuid.uuid4()),
            amount=order.total(),
            email=request.user.email,
            description=f"payment for order {order.code} ({order.pk}) by {request.user.email}",
        )

        success_url = request.build_absolute_uri(
            reverse('cart:step4b_verify_payment',
                    kwargs={'payment_uuid': stripe_payment.uuid,
                            'session_id': 'CHECKOUT_SESSION_ID'
                    }
        ))
        # XXX {} must not be url-encoded
        success_url = success_url.replace('CHECKOUT_SESSION_ID', '{CHECKOUT_SESSION_ID}')

        cancel_url = request.build_absolute_uri(
            reverse('cart:step4_payment',
                    kwargs={'order_uuid': order.uuid},
        ))
        line_items = []
        line_items.append({
            'name': 'Invoice',
            'description': stripe_payment.description,
            'amount': stripe_payment.amount_for_stripe(),
            'currency': STRIPE_PAYMENTS_CURRENCY,
            'quantity': 1,
        })

        session = stripe.checkout.Session.create(
            payment_intent_data=dict(
            metadata={
                'order': request.build_absolute_uri(reverse('admin:assopy_order_change', args=(order.id,))),
                'order_uuid': order.uuid,
                'order_code': order.code,
                'order_pk': order.pk,
            }),
            # XXX Setting email disables editing it. Not sure we want that.
            # customer_email=stripe_payment.email,
            success_url=success_url,
            cancel_url=cancel_url,
            payment_method_types=['card'],
            line_items=line_items,
        )

        stripe_payment.session_id = session.id
        stripe_payment.save()

        return session

    except stripe.error.StripeError as e:
        stripe_error = e.json_body['error']
        stripe_payment.status = stripe_payment.STATUS_CHOICES.FAILED
        stripe_payment.message = (
            f"{stripe_error['type']} -- {stripe_error['message']}"
        )
        stripe_payment.save()

        raise PaymentError(stripe_error)


def verify_payment(stripe_payment, session_id):
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
        if payment_intent.status == 'succeeded' and  payment_intent.amount_received == stripe_payment.amount_for_stripe():
            charge = payment_intent.charges.data[0]
            stripe_payment.status = stripe_payment.STATUS_CHOICES.SUCCESSFUL
            stripe_payment.charge_id = charge.id
            stripe_payment.save()
        else:
            stripe_payment.status = stripe_payment.STATUS_CHOICES.FAILED
            stripe_payment.message = (
                "There was an error processing your payment."
            )
            stripe_payment.save()
            raise PaymentError({'type': 'unknown',
                                'message': 'error processing payment'})


    except stripe.error.StripeError as e:
        stripe_error = e.json_body['error']
        stripe_payment.status = stripe_payment.STATUS_CHOICES.FAILED
        stripe_payment.message = (
            f"{stripe_error['type']} -- {stripe_error['message']}"
        )
        stripe_payment.save()

        raise PaymentError(stripe_error)

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
