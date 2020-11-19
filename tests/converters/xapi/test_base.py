"""Tests for the base xapi converter"""

import pytest

from ralph.converters.xapi.base import BaseXapiConverter
from ralph.converters.xapi.constants import HOME_PAGE

from tests.fixtures.logs import EventType


class BaseXapiConverterMock(BaseXapiConverter):
    """Dummy implementation with required abstract methods"""

    def get_verb_kwargs(self):  # pylint: disable=no-self-use
        """Dummy get_verb_kwargs implementation"""

        return {}

    def get_object(self):  # pylint: disable=no-self-use
        """Dummy get_object implementation"""

        return None


SCHEMA = BaseXapiConverterMock()


@pytest.mark.parametrize("user_id", [None, "", 123])
@pytest.mark.parametrize("username, actor_name", [["", "anonymous"], ["user", "user"]])
def test_base_xapi_converter_returns_actor_timestamp_and_context(
    event, user_id, username, actor_name
):
    """Test that BaseXapiConverter returns actor, timestamp and context"""

    event_args = {"username": username, "context_args": {"user_id": user_id}}
    base_event = event(1, EventType.BASE_EVENT, **event_args).iloc[0].to_dict()
    xapi_event = SCHEMA.dump(SCHEMA.load(base_event))
    assert xapi_event["actor"]["objectType"] == "Agent"
    assert xapi_event["actor"]["account"]["name"] == actor_name
    assert xapi_event["actor"]["account"]["homePage"] == HOME_PAGE
    assert xapi_event["timestamp"] == base_event["time"]
    course_user_tags = base_event["context"].get("course_user_tags", {})
    user_id_extension = {}
    if user_id is not None:
        user_id_extension["https://www.fun-mooc.fr/extension/user_id"] = user_id
    assert xapi_event["context"] == {
        "extensions": {
            "https://www.fun-mooc.fr/extension/accept_language": base_event[
                "accept_language"
            ],
            "https://www.fun-mooc.fr/extension/agent": base_event["agent"],
            "https://www.fun-mooc.fr/extension/course_id": base_event["context"][
                "course_id"
            ],
            "https://www.fun-mooc.fr/extension/course_user_tags": course_user_tags,
            "https://www.fun-mooc.fr/extension/host": base_event["host"],
            "https://www.fun-mooc.fr/extension/ip": base_event["ip"],
            "https://www.fun-mooc.fr/extension/org_id": base_event["context"]["org_id"],
            "https://www.fun-mooc.fr/extension/referer": base_event["referer"],
            **user_id_extension,
        },
        "platform": HOME_PAGE,
    }


def test_get_object_and_get_verb_kwargs_methods_are_required():
    """Test that get_object and get_verb_kwargs methodes are required to be implemented"""

    schema = BaseXapiConverter()
    with pytest.raises(NotImplementedError, match="get_object should be implemented"):
        schema.get_object()
    with pytest.raises(
        NotImplementedError, match="get_verb_kwargs should be implemented"
    ):
        schema.get_verb_kwargs()
