"""
Tests for the base ora event schema
"""
import pytest
from marshmallow import ValidationError

from tests.fixtures.logs import EventType, _event
from tests.schema.edx.test_common import check_error


@pytest.fixture()
def base_ora_event():
    """Returns a base event generator that generates size number of events"""
    return lambda size=1, **kwargs: _event(size, EventType.BASE_ORA_EVENT, **kwargs)


def test_invalid_username_value(base_ora_event):
    """ValidationError should be raised if the username value
    is empty or less than 2 characters
    """
    with pytest.raises(ValidationError) as excinfo:
        base_ora_event(1, username="")
    check_error(excinfo, "Length must be between 2 and 30.")
    with pytest.raises(ValidationError):
        base_ora_event(1, username="1")
    with pytest.raises(ValidationError):
        base_ora_event(1, username=1234)
    with pytest.raises(ValidationError):
        base_ora_event(1, username="more_than_30_characters_long_for_sure")


def test_invalid_page_value(base_ora_event):
    """ValidationError should be raised if the page value
    is not x_module
    """
    with pytest.raises(ValidationError):
        base_ora_event(1, page="not_x_module")
