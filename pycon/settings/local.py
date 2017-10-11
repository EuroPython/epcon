# Mandatory settings
# ------------------
import os

DEBUG = True

SECRET_KEY = "your-secret-key"

# Put your google maps key here
CONFERENCE_GOOGLE_MAPS = {
    'key': '',
    'country': 'it',
}

# Paypal merchant email
PAYPAL_RECEIVER_EMAIL = os.environ.get("PAYPAL_RECEIVER_EMAIL")

# If the merchant account is a debug one set this flag to True
PAYPAL_TEST = os.environ.get("PAYPAL_TEST") or True

# Janrain account
ASSOPY_JANRAIN = {
    'domain': '',
    'app_id': '',
    'secret': '',
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Sentry account
RAVEN_CONFIG = {
    'dsn': '',
}
