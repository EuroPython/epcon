from django.urls import reverse


def test_p3_profile_avatar(db, user_client):
    url = reverse('p3-profile-avatar', args=[user_client.user.attendeeprofile.slug])
    response = user_client.get(url)
    assert response.status_code == 200
