"""
Improved tests for ep2019+ based on the new cart implementation
"""
import pytest


@pytest.mark.xfail
def test_user_can_configure_their_ticket(db):
    assert False


@pytest.mark.xfail
def test_user_can_modify_their_tickets(db):
    assert False


@pytest.mark.xfail
def test_user_cannot_modify_tickets_that_are_not_theirs(db):
    assert False


@pytest.mark.xfail
def test_user_can_assign_their_ticket(db):
    assert False


@pytest.mark.xfail
def test_user_cannot_assign_not_their_own_ticket(db):
    assert False
