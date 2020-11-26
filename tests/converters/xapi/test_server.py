"""Tests for the server event xapi converter"""

import json

import pandas as pd
import pytest
from marshmallow import ValidationError

from ralph.converters.xapi.base import BaseXapiConverter
from ralph.converters.xapi.server import ServerXapiConverter
from ralph.schemas.edx.server import ServerEventSchema

SCHEMA = ServerEventSchema()
CONVERTER = ServerXapiConverter()
PLATFORM = "https://www.fun-mooc.fr"
BaseXapiConverter._platform = PLATFORM  # pylint: disable=protected-access


def test_valid_server_events_should_match_expected_xapi_statements():
    """Test the xapi conversion of server events defined in the data directory"""

    event_name = "server_event"
    current_path = f"tests/data/current_edx_events/{event_name}.json"
    expected_path = f"tests/data/expected_xapi_statements/{event_name}.json"
    edx = pd.read_json(current_path, dtype=False, convert_dates=False)
    xapi = pd.read_json(expected_path, dtype=False, convert_dates=False)
    try:
        for i, event in edx.iterrows():
            event_dict = event.to_dict()
            expected_xapi_statement = xapi.iloc[i].to_dict()
            event_dict.pop("__comment", None)
            expected_xapi_statement.pop("__comment", None)
            event_str = json.dumps(event_dict)
            converted_xapi_statement = CONVERTER.convert(event_str)
            converted_xapi_statement_dict = json.loads(converted_xapi_statement)
            assert converted_xapi_statement_dict == expected_xapi_statement
    except ValidationError:
        pytest.fail("Valid server events should not raise exceptions")
