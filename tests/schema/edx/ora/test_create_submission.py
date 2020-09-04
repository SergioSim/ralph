"""
Tests for the CreateSubmission event schema
"""
# pylint: disable=redefined-outer-name
import operator

import pytest
from marshmallow import ValidationError

from ralph.schemas.edx.ora.create_submission import CreateSubmissionSchema

from tests.fixtures.logs import EventType, _event
from tests.schema.edx.test_common import check_error, check_loading_valid_events


@pytest.fixture()
def create_submission():
    """Returns a save_submission event generator that generates size number of events"""
    return lambda size, **kwargs: _event(size, EventType.CREATE_SUBMISSION, **kwargs)


def test_loading_valid_events_should_not_raise_exceptions():
    """check that loading valid events does not raise exceptions"""
    check_loading_valid_events(CreateSubmissionSchema(), "create_submission")


def test_invalid_event_type_value(create_submission):
    """ValidationError should be raised if the event_type value
    is not openassessmentblock.create_submission
    """
    with pytest.raises(ValidationError) as excinfo:
        create_submission(1, event_type="problem_check")
    check_error(
        excinfo,
        "The event event_type field is not `openassessmentblock.create_submission`",
    )


def test_invalid_context_path_value(create_submission):
    """ValidationError should be raised if the path value
    does not end with /submit
    """
    context = create_submission(1).iloc[0]["context"]
    context["path"] = "{}_not_submit".format(context["path"])
    with pytest.raises(ValidationError) as excinfo:
        create_submission(1, context=context)
    check_error(
        excinfo, "context.path should end with: /handler/submit", operator.contains,
    )
