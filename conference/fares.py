from django.conf import settings

from model_utils import Choices

from assopy.models import Vat, VatFare
from conference.models import FARE_TICKET_TYPES, Conference, Fare, Ticket


# due to historical reasons this one is basically hardcoded in various places.
SOCIAL_EVENT_FARE_CODE = "VOUPE03"
SIM_CARD_FARE_CODE = "SIM1"

# The ticket code follows this layout:
#   "T<type><variant><group>"
#   e.g. "TRSP" - standard conference ticket at the regular price for
#   personal use

FARE_CODE_TYPES = Choices(
    ("E", "EARLY_BIRD", "Early Bird"),
    ("R", "REGULAR",    "Regular"),
    ("D", "ON_DESK",    "On Desk"),
)

FARE_CODE_VARIANTS = Choices(
    ("S", "STANDARD", "Standard"),
    ("L", "LIGHT",    "Standard Light (no trainings)"),
    ("T", "TRAINING", "Trainings (ep2018+)"),   # Starting with EP2018
    ("C", "COMBINED", "Combined (ep2019+)"),    # Starting with EP2019
    ("P", "SPRINT", "Sprints only"),            # Starting with EP2020
    ("D", "DAYPASS",  "Day Pass"),
    ("V", "STREAM",  "Stream only"),            # Starting with EP2021
)

# Variants eligible for talk voting
FARE_CODE_TALK_VOTING_VARIANTS = (
    "S", "L", "T", "C"
    )

# Variants for speaker tickets (ones for which we issues coupons)
FARE_CORE_SPEAKER_TICKET_VARIANTS = (
    "S", "L", "T", "C",
    )

FARE_CODE_GROUPS = Choices(
    ("S", "STUDENT",  "Student"),
    ("P", "PERSONAL", "Personal"),
    ("C", "COMPANY",  "Business"),
    # Note: We are using the term "Business ticket" on the website, but
    # Company ticket in the code (for historical reasons)
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
        FARE_CODE_VARIANTS.SPRINT:   "^T.P.$",
        FARE_CODE_VARIANTS.DAYPASS:  "^T.D.$",
    },
    "groups": {
        FARE_CODE_GROUPS.STUDENT:    "^T..S$",
        FARE_CODE_GROUPS.PERSONAL:   "^T..P$",
        FARE_CODE_GROUPS.COMPANY:    "^T..C$",
    }
}

TALK_VOTING_CODE_REGEXP = (
    "^T.[" + ''.join(FARE_CODE_TALK_VOTING_VARIANTS) + "].$")

SPEAKER_TICKET_CODE_REGEXP = (
    "^T.[" + ''.join(FARE_CORE_SPEAKER_TICKET_VARIANTS) + "].$")

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
    fare_codes[SIM_CARD_FARE_CODE] = "SIM Card"
    return fare_codes


ALL_POSSIBLE_FARE_CODES = all_possible_fare_codes()

def talk_voting_fare_codes():
    fare_codes = {
        "T" + type_code + variant_code + group_code:
        "%s %s %s" % (type_name, variant_name, group_name)

        for type_code, type_name       in FARE_CODE_TYPES._doubles
        for variant_code, variant_name in FARE_CODE_VARIANTS._doubles
        for group_code, group_name     in FARE_CODE_GROUPS._doubles
        if variant_code in FARE_CODE_TALK_VOTING_VARIANTS
    }
    return fare_codes

TALK_VOTING_FARE_CODES = talk_voting_fare_codes()

def is_fare_code_valid(fare_code):
    return fare_code in ALL_POSSIBLE_FARE_CODES


def is_early_bird_sold_out():
    eb_ticket_orders = Ticket.objects.filter(
        fare__conference=settings.CONFERENCE_CONFERENCE,
        frozen=False,
        # orderitem__order___complete=True,
        fare__code__regex=FARE_CODE_REGEXES["types"][FARE_CODE_TYPES.EARLY_BIRD]
    )

    return eb_ticket_orders.count() >= settings.EARLY_BIRD_ORDER_LIMIT


def get_available_fares(date):
    """
    Returns all fares that where available during a given point in time,
    regardless of whether they were sold out or not.
    """
    fares = Fare.objects.filter(
        start_validity__lte=date,
        end_validity__gte=date,
    )

    if is_early_bird_sold_out():
        fares = fares.exclude(
            code__regex=FARE_CODE_REGEXES["types"][FARE_CODE_TYPES.EARLY_BIRD]
        )

    return fares


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
    elif code == SIM_CARD_FARE_CODE:
        ticket_type = FARE_TICKET_TYPES.other

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
        defaults=dict(
            description=name,
            name=name,
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


def set_other_fares_dates(conference, start_date, end_date):
    assert start_date <= end_date

    other_fares = Fare.objects.filter(
        conference=conference,
        code__in=[SOCIAL_EVENT_FARE_CODE, SIM_CARD_FARE_CODE],
    )

    other_fares.update(start_validity=start_date, end_validity=end_date)


def set_early_bird_fare_dates(conference, start_date, end_date):
    assert start_date <= end_date

    early_birds = Fare.objects.filter(
        conference=conference,
        code__regex=FARE_CODE_REGEXES["types"][FARE_CODE_TYPES.EARLY_BIRD],
    )
    assert (
        early_birds.count()
        == len(FARE_CODE_VARIANTS) * len(FARE_CODE_GROUPS)
    )
    early_birds.update(start_validity=start_date, end_validity=end_date)


def set_regular_fare_dates(conference, start_date, end_date):
    assert start_date <= end_date

    fares = Fare.objects.filter(
        conference=conference,
        code__regex=FARE_CODE_REGEXES['types'][FARE_CODE_TYPES.REGULAR]
    )
    assert (
        fares.count()
        == len(FARE_CODE_VARIANTS) * len(FARE_CODE_GROUPS)
    )
    fares.update(start_validity=start_date, end_validity=end_date)
