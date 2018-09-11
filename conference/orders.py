# coding: utf-8

from __future__ import unicode_literals, absolute_import

from django.db.models import Max

from assopy.models import Order


ORDER_CODE_PREFIX = "O/"
ORDER_CODE_TEMPLATE = "O/%(year_two_digits)s.%(sequential_id)s"


def increment_order_code(code):
    NUMBER_OF_DIGITS_WITH_PADDING = 4

    prefix_with_year, number = code.split('.')
    number = str(int(number) + 1).zfill(NUMBER_OF_DIGITS_WITH_PADDING)
    return "{}.{}".format(prefix_with_year, number)


def latest_order_code_for_year(year):
    """
    returns latest used order.code in a given year.
    rtype – string or None
    """
    assert 2016 <= year <= 2020, year

    orders = Order.objects.filter(
        code__startswith=ORDER_CODE_PREFIX,
        created__year=year,
    )

    return orders.aggregate(max=Max('code'))['max']


def next_order_code_for_year(year):
    assert 2016 <= year <= 2020, year

    current_code = latest_order_code_for_year(year)
    if current_code:
        next_code = increment_order_code(current_code)
        return next_code

    # if there are no current codes, return the first one
    template = ORDER_CODE_TEMPLATE
    return template % {'year_two_digits': year % 1000, 'sequential_id': '0001'}
