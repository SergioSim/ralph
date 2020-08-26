"""
Tests for the SaveSubmission event schema
"""
# pylint: disable=redefined-outer-name
import pandas as pd
import pytest
from marshmallow import ValidationError

from ralph.schemas.edx.ora.save_submission import SaveSubmissionSchema

from tests.schema.edx.test_common import check_error, check_loading_valid_events
from tests.fixtures.logs import EventType, _event


@pytest.fixture()
def save_submission():
    """Returns a save_submission event generator that generates size number of events"""
    return lambda size, **kwargs: _event(size, EventType.SAVE_SUBMISSION, **kwargs)


def test_loading_valid_events_should_not_raise_exceptions():
    """check that loading valid events does not raise exceptions"""
    check_loading_valid_events(SaveSubmissionSchema(), "save_submission")


def test_invalid_username_value(save_submission):
    """ValidationError should be raised if the username value
    is empty or less than 2 characters
    """
    with pytest.raises(ValidationError) as excinfo:
        save_submission(1, username="")
    check_error(excinfo, "Length must be between 2 and 30.")   
    with pytest.raises(ValidationError):
        save_submission(1, username="1")
    with pytest.raises(ValidationError):
        save_submission(1, username=1234)
    with pytest.raises(ValidationError):
        save_submission(1, username="more_than_30_characters_long_for_sure")


def test_invalid_event_type_value(save_submission):
    """ValidationError should be raised if the event_type value
    is not openassessmentblock.save_submission
    """
    with pytest.raises(ValidationError):
        save_submission(1, event_type="problem_check")


def test_invalid_page_value(save_submission):
    """ValidationError should be raised if the page value
    is not x_module
    """
    with pytest.raises(ValidationError):
        save_submission(1, page="not_x_module")


def test_invalid_context_path_value(save_submission):
    """ValidationError should be raised if the path value
    does not end with /save_submission
    """
    context = save_submission(1).iloc[0]["context"]
    context["path"] = "{}_not_save_submission".format(context["path"])
    with pytest.raises(ValidationError):
        save_submission(1, context=context)


def test_invalid_event_value(save_submission):
    """Validation error should be raised if the event field value
    is not a parsable json containing the key `parts` or the corresponding
    value is not a array of json objects containing the  key `text`
    """
    with pytest.raises(ValidationError) as excinfo:
        save_submission(1, event="not a parsable json string")
