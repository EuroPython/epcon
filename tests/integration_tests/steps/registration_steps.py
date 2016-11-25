from django.contrib.auth import get_user_model

from pytest_bdd import given, when, then, parsers


@given(parsers.parse('that the user has filled the registration form with'))
def fill_registration_form(get_page, datatable):
    for row in datatable[1]:
        field_name = row[0]
        value = row[1]

        getattr(get_page, field_name).send_keys(value)


@when('he submits the form')
def form_submit(get_page):
    get_page.form.submit()


@then('he should have an account with those information')
def account_data_check(get_page, datatable):
    data = {}

    for row in datatable[1]:
        data[row[0]] = row[1]

    try:
        user = get_user_model().objects.get(email=data['email'])
    except get_user_model().DoesNotExist:
        assert False, 'User with email {} not found'.format(data['email'])

    for key, value in data.iteritems():
        if key == 'password':
            assert user.check_password(value) is True, 'Password not matching'
            continue

        db_value = getattr(user, key)
        assert db_value == value, 'Key {} not matching {} != {}'.format(key, db_value, value)
