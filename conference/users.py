# coding: utf-8

"""
This module takes care of a lot of user related things.
It's a good place to put validators and user management functions/classes
"""

import hashlib
import uuid

RANDOM_USERNAME_LENGTH = 10


def generate_random_username():
    """Returns md5 of uuid that can be later used as a username

    Using md5 instead of raw uuid so that it's later not confusing when we
    introduce proper uuids for Users. We also don't need that many options so
    we can just grab first few characters
    """
    return hashlib.md5(str(uuid.uuid4())).hexdigest()[:RANDOM_USERNAME_LENGTH]
