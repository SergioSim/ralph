"""Tests for the server event xapi converter"""

import json

import pandas as pd
import pytest
from marshmallow import ValidationError

from ralph.converters.xapi.base import BaseXapiConverter
from ralph.converters.xapi.server import ServerXapiConverter
from ralph.schemas.edx.server import ServerEventSchema

from tests.fixtures.logs import EventType

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
            converted_xapi_statement = CONVERTER.convert(event_dict)
            converted_xapi_statement_dict = json.loads(converted_xapi_statement)
            assert converted_xapi_statement_dict == expected_xapi_statement
    except ValidationError:
        pytest.fail("Valid server events should not raise exceptions")


def test_converting_invalid_server_event_should_return_none(event):
    """The converter should return None for invalid events"""

    server_event = event(EventType.SERVER)
    server_event["username"] = "This user name is more than 32 chars long!"
    assert CONVERTER.convert(server_event) is None


@pytest.mark.parametrize("user_id", [None, "", 123])
@pytest.mark.parametrize("username, actor_name", [["", "anonymous"], ["user", "user"]])
def test_server_xapi_converter_returns_actor_timestamp_and_context(
    event, user_id, username, actor_name
):
    """Test that ServerXapiConverter returns actor, timestamp and context"""

    event_args = {"username": username, "context_args": {"user_id": user_id}}
    server_event = event(EventType.SERVER, **event_args)
    # convert server_event_str
    xapi_event_str = CONVERTER.convert(server_event)
    xapi_event = json.loads(xapi_event_str)
    assert xapi_event["actor"]["objectType"] == "Agent"
    assert xapi_event["actor"]["account"]["name"] == actor_name
    assert xapi_event["actor"]["account"]["homePage"] == PLATFORM
    assert xapi_event["timestamp"] == server_event["time"]
    course_user_tags = server_event["context"].get("course_user_tags", {})
    user_id_extension = {}
    if user_id is not None:
        user_id_extension["https://www.fun-mooc.fr/extension/user_id"] = user_id
    assert xapi_event["context"] == {
        "extensions": {
            "https://www.fun-mooc.fr/extension/accept_language": server_event[
                "accept_language"
            ],
            "https://www.fun-mooc.fr/extension/agent": server_event["agent"],
            "https://www.fun-mooc.fr/extension/course_id": server_event["context"][
                "course_id"
            ],
            "https://www.fun-mooc.fr/extension/course_user_tags": course_user_tags,
            "https://www.fun-mooc.fr/extension/host": server_event["host"],
            "https://www.fun-mooc.fr/extension/ip": server_event["ip"],
            "https://www.fun-mooc.fr/extension/org_id": server_event["context"]["org_id"],
            "https://www.fun-mooc.fr/extension/path": server_event["context"]["path"],
            "https://www.fun-mooc.fr/extension/referer": server_event["referer"],
            "https://www.fun-mooc.fr/extension/request": server_event["event"],
            **user_id_extension,
        },
        "platform": PLATFORM,
    }