"""
Gravatar-related functions.
"""
import hashlib
import urllib.error
import urllib.parse
import urllib.request


def gravatar(email, size=80, default='identicon', rating='r',
             protocol='https'):
    """Create a Gravatar URL given the user email address."""

    if protocol == 'https':
        host = 'https://secure.gravatar.com'
    else:
        host = 'http://www.gravatar.com'

    # Remember: hash funcions expect bytes objects, not strings.
    lowercase_email = email.lower()
    if not isinstance(lowercase_email, bytes):
        # Encode it!
        lowercase_email = lowercase_email.encode('utf-8')

    gravatar_url = '{}/avatar/{}?'.format(host, hashlib.md5(lowercase_email).hexdigest())
    gravatar_url += urllib.parse.urlencode({
        'default': default,
        'size': size,
        'rating': rating,
    })
    return gravatar_url
