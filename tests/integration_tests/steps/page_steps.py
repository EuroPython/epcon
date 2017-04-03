from pytest_bdd import given, parsers

from tests.integration_tests.users.registration_page import RegistrationPage


AVAILABLE_PAGES = {
    'registration': RegistrationPage,
}


@given(parsers.parse('the user is on the {page} page'))
def get_page(page, live_server, selenium):
    if page not in AVAILABLE_PAGES:
        # Warn about the invalid page?
        raise KeyError('Page {} is not a valid page. Valid pages: {}'.format(page, AVAILABLE_PAGES))

    page_cls = AVAILABLE_PAGES[page]
    page = page_cls(base_url=live_server.url, selenium=selenium)
    page.open()
    return page
