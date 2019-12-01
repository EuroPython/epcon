from django.contrib.auth import get_user_model

import pytest

from assopy.models import AssopyUser


@pytest.mark.parametrize(
    "first_name,last_name,expected", [
        ("John", "Doe", ("John", "Doe")),
        ("John Doe", "Doe", ("John", "Doe")),
        # let's get some utf8 going
        ("Skřŷźňǎ", "Labrŷẓňă", ("Skřŷźňǎ", "Labrŷẓňă")),
        ("Skřŷźňǎ Labrŷẓňă", "Labrŷẓňă", ("Skřŷźňǎ", "Labrŷẓňă")),
        # Having identical first and last names is unusual but not as rare as you'd think:
        # https://en.wikipedia.org/wiki/List_of_people_with_reduplicated_names
        ("Thomas", "Thomas", ("Thomas", "Thomas")),
        ("Thomas Thomas", "Thomas", ("Thomas", "Thomas")),
    ])
def test_name_tuple(first_name, last_name, expected):
    user = get_user_model()(first_name=first_name, last_name=last_name)
    assopy_user = AssopyUser(user=user)
    assert assopy_user.name_tuple() == expected
