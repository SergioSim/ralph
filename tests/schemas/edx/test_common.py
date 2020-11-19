"""Common function definitions for edx event tests"""
import operator

import pandas as pd
import pytest
from marshmallow import ValidationError


def check_error(excinfo, message, operator_type=operator.eq, error_key=None):
    """Compare error `excinfo` message with operator_type on `message`"""
    key = next(iter(excinfo.value.messages))
    if error_key:
        key = error_key
    if isinstance(excinfo.value.messages[key], dict):
        first_key = next(iter(excinfo.value.messages[key]))
        value = excinfo.value.messages[key][first_key][0]
    else:
        value = excinfo.value.messages[key][0]
    assert operator_type(value, message)


def check_loading_valid_events(schema, file_name):
    """Test that loading valid events does not raise exceptions

    Args:
        schema (marshmallow.Schema): the event schema
        file_name (String): name of the file containing valid events
    """
    events = pd.read_json(
        f"tests/data/current_edx_events/{file_name}.json", dtype=False
    )
    try:
        for _, event in events.iterrows():
            event_dict = event.to_dict()
            event_dict.pop("__comment", None)
            schema.load(event_dict)
    except ValidationError:
        pytest.fail(f"Valid {file_name} events should not raise exceptions")
