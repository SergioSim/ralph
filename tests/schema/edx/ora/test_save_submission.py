"""
Tests for the SaveSubmission event schema
"""
# pylint: disable=redefined-outer-name
import pandas as pd
import pytest
from marshmallow import ValidationError

from ralph.schemas.edx.ora.save_submission import SaveSubmissionSchema

from tests.fixtures.logs import EventType, _event

SCHEMA = SaveSubmissionSchema()


@pytest.fixture()
def save_submission():
    """Returns a save_submission event generator that generates size number of events"""
    return lambda size, **kwargs: _event(size, EventType.SAVE_SUBMISSION, **kwargs)


def test_loading_valid_events_should_not_raise_exceptions():
    """check that loading valid events does not raise exceptions
    """
    chunks = pd.read_json("tests/data/save_submission.log", lines=True)
    try:
        for _, chunk in chunks.iterrows():
            SCHEMA.load(chunk.to_dict())
    except ValidationError:
        pytest.fail("valid feedback_displayed events should not raise exceptions")
