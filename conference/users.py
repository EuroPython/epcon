"""
This module takes care of a lot of user related things.
It's a good place to put validators and user management functions/classes
"""
import os


RANDOM_USERNAME_LENGTH = 12


def generate_random_username():
    """Returns random username of length set by RANDOM_USERNAME_LENGTH
    
       The generated names will always start with 'ep' to make sure that we
       don't generate numeric only names.
       
    """
    return 'ep' + os.urandom(100).hex()[:RANDOM_USERNAME_LENGTH-2]
