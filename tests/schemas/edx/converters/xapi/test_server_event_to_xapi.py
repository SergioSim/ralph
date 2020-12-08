"""Tests for the server event xapi converter"""

import json

import pytest

from ralph.schemas.edx.converters.xapi.base import BaseXapiConverter
from ralph.schemas.edx.converters.xapi.server_event_to_xapi import ServerEventToXapi
from ralph.schemas.edx.server_event import ServerEventSchema

from tests.fixtures.logs import EventType

SCHEMA = ServerEventSchema()
CONVERTER = ServerEventToXapi()
PLATFORM = "https://www.fun-mooc.fr"
BaseXapiConverter._platform = PLATFORM  # pylint: disable=protected-access
CONVERTER.init_flat_conversion_array()


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
    """Test that ServerEventToXapi returns actor, timestamp and context"""

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
    user_id = user_id if user_id else ""
    assert xapi_event["context"] == {
        "extensions": {
            "https://www.edx.org/extension/accept_language": server_event[
                "accept_language"
            ],
            "https://www.edx.org/extension/agent": server_event["agent"],
            "https://www.edx.org/extension/course_id": server_event["context"][
                "course_id"
            ],
            "https://www.edx.org/extension/course_user_tags": course_user_tags,
            "https://www.edx.org/extension/host": server_event["host"],
            "https://www.edx.org/extension/ip": server_event["ip"],
            "https://www.edx.org/extension/org_id": server_event["context"]["org_id"],
            "https://www.edx.org/extension/path": server_event["context"]["path"],
            "https://www.edx.org/extension/referer": server_event["referer"],
            "https://www.edx.org/extension/request": server_event["event"],
            "https://www.edx.org/extension/user_id": user_id,
        },
        "platform": PLATFORM,
    }
