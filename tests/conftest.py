import pytest

from . import factories


@pytest.fixture
def user():
    user = factories.UserFactory()
    user.attendeeprofile.setBio('bio')
    return user


@pytest.fixture
def user_client(client):
    user = factories.UserFactory()
    user.attendeeprofile.setBio('bio')
    client.login(email=user.email, password='password123')
    client.user = user
    yield client


@pytest.fixture
def ep_admin_client(client):
    """
    Custom admin client for EP so that it creates all required user-related
    objects like AssopyUser or AttendeeProfile
    """
    user = factories.UserFactory(is_staff=True)
    user.attendeeprofile.setBio('bio')
    client.login(email=user.email, password='password123')
    client.user = user
    yield client
