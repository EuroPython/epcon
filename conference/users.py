# coding: utf-8

"""
This module takes care of a lot of user related things.
It's a good place to put validators and user management functions/classes
"""

import os


RANDOM_USERNAME_LENGTH = 10


def generate_random_username():
    """Returns random username of length set by RANDOM_USERNAME_LENGTH"""
    return os.urandom(100).hex()[:RANDOM_USERNAME_LENGTH]
