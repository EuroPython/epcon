from django.conf import settings
from model_utils import Choices

from assopy.models import Vat, VatFare
from conference.models import FARE_TICKET_TYPES, Conference, Fare


# due to historical reasons this one is basically hardcoded in various places.
SOCIAL_EVENT_FARE_CODE = 'VOUPE03'
SPECIAL_CODES = [SOCIAL_EVENT_FARE_CODE]

FARE_CODE_TYPES = Choices(
    ("E", "EARLY_BIRD", "Early Bird"),
    ("R", "REGULAR",    "Regular"),
    ("D", "ON_DESK",    "On Desk"),
)

FARE_CODE_VARIANTS = Choices(
    ("S", "STANDARD", "Standard"),
    ("L", "LIGHT",    "Standard Light (no trainings)"),
    ("T", "TRAINING", "Trainings (ep2018+)"),
    ("C", "COMBINED", "Combined (ep2019+)"),
    ("D", "DAYPASS",  "Day Pass"),
)

FARE_CODE_GROUPS = Choices(
    ("S", "STUDENT",  "Student"),
    ("P", "PERSONAL", "Personal"),
    ("C", "COMPANY",  "Company"),
)

FARE_CODE_REGEXES = {
    "types": {
        FARE_CODE_TYPES.EARLY_BIRD:  "^TE..$",
        FARE_CODE_TYPES.REGULAR:     "^TR..$",
        FARE_CODE_TYPES.ON_DESK:     "^TD..$",
    },
    "variants": {
        FARE_CODE_VARIANTS.STANDARD: "^T.S.$",
        FARE_CODE_VARIANTS.LIGHT:    "^T.L.$",
        FARE_CODE_VARIANTS.TRAINING: "^T.T.$",
        FARE_CODE_VARIANTS.COMBINED: "^T.C.$",
        FARE_CODE_VARIANTS.DAYPASS:  "^T.D.$",
    },
    "groups": {
        FARE_CODE_GROUPS.STUDENT:    "^T..S$",
        FARE_CODE_GROUPS.PERSONAL:   "^T..P$",
        FARE_CODE_GROUPS.COMPANY:    "^T..C$",
    }
}


class FareIsNotAvailable(Exception):
    pass


def all_possible_fare_codes():
    fare_codes = {
        "T" + type_code + variant_code + group_code:
        "%s %s %s" % (type_name, variant_name, group_name)

        for type_code, type_name       in FARE_CODE_TYPES._doubles
        for variant_code, variant_name in FARE_CODE_VARIANTS._doubles
        for group_code, group_name     in FARE_CODE_GROUPS._doubles
    }

    fare_codes[SOCIAL_EVENT_FARE_CODE] = "Social Event"
    return fare_codes


ALL_POSSIBLE_FARE_CODES = all_possible_fare_codes()


def is_fare_code_valid(fare_code):
    return fare_code in ALL_POSSIBLE_FARE_CODES


def get_available_fares(date):
    """
    Returns all fares that where available during a given point in time,
    regardless of whether they were sold out or not.
    """
    return Fare.objects.filter(
        start_validity__lte=date,
        end_validity__gte=date,
    )


def get_available_fares_as_dict(date):
    return {f.code: f for f in get_available_fares(date)}


def get_prices_of_available_fares(date):
    codes_with_prices = get_available_fares(date).values_list('code', 'price')
    return {f[0]: f[1] for f in codes_with_prices}


def create_fare_for_conference(code, conference, price,
                               start_validity, end_validity,
                               vat_rate):

    assert is_fare_code_valid(code)
    assert isinstance(conference, str), "conference should be a string"
    assert isinstance(vat_rate, Vat)
    if start_validity is not None and end_validity is not None:
        assert start_validity <= end_validity

    if code == SOCIAL_EVENT_FARE_CODE:
        ticket_type = FARE_TICKET_TYPES.event
    else:
        ticket_type = FARE_TICKET_TYPES.conference

    # This is inefficient, we should pass Conference object as argument instead
    # of name.
    conference, _ = Conference.objects.get_or_create(
        code=conference,
    )
    if not conference.name:
        conference.name = settings.CONFERENCE_NAME
        conference.save()

    recipient_type = code[3].lower()  # same as lowercase last letter of code

    name = "%s - %s" % (conference.name, ALL_POSSIBLE_FARE_CODES[code])
    fare, _ = Fare.objects.get_or_create(
        conference=conference.code,
        code=code,
        name=name,
        defaults=dict(
            description=name,
            price=price,
            recipient_type=recipient_type,
            ticket_type=ticket_type,
            start_validity=start_validity,
            end_validity=end_validity,
        )
    )
    VatFare.objects.get_or_create(fare=fare, vat=vat_rate)
    return fare


def pre_create_typical_fares_for_conference(conference, vat_rate,
                                            print_output=False):
    fares = []

    for fare_code in ALL_POSSIBLE_FARE_CODES.keys():
        fare = create_fare_for_conference(
            code=fare_code,
            conference=conference,
            price=210,  # random price, we'll change it later (div. by 3)
            start_validity=None, end_validity=None,
            vat_rate=vat_rate,
        )
        if print_output:
            print("Created fare %s" % fare)
        fares.append(fare)

    return fares


def set_early_bird_fare_dates(conference, start_date, end_date):
    assert start_date <= end_date

    early_birds = Fare.objects.filter(
        conference=conference,
        code__regex=FARE_CODE_REGEXES['types'][FARE_CODE_TYPES.EARLY_BIRD]
    )
    assert early_birds.count() == len(FARE_CODE_VARIANTS) * len(FARE_CODE_GROUPS) == 3 * 5
    early_birds.update(start_validity=start_date, end_validity=end_date)


def set_regular_fare_dates(conference, start_date, end_date):
    assert start_date <= end_date

    fares = Fare.objects.filter(
        conference=conference,
        code__regex=FARE_CODE_REGEXES['types'][FARE_CODE_TYPES.REGULAR]
    )
    assert fares.count() == len(FARE_CODE_VARIANTS) * len(FARE_CODE_GROUPS) == 3 * 5
    fares.update(start_validity=start_date, end_validity=end_date)
