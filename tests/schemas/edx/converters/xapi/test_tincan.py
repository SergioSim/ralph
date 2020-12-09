"""Test that all defined edx_to_xapi converters produce valid xAPI statements using TinCanPython"""

import copy
import json
from io import StringIO

import pytest
from tincan import Statement

from ralph.schemas.edx.converters.xapi_converter_selector import (
    Converters,
    XapiConverterSelector,
)

from tests.fixtures.logs import EventType, event_generator

CONVERTER = XapiConverterSelector("https://fun-mooc.fr")
EVENT_COUNT = 200
EVENTS = {Converters.SERVER: event_generator(EventType.SERVER, EVENT_COUNT)}
CONVERTOR_STATEMENTS = []


def fill_convertor_statements():
    """Prepare statents for parametrized tests"""

    for converter, events in EVENTS.items():
        with StringIO() as file:

            # Write events to file
            for event in events:
                file.write(f"{json.dumps(event)}\n")
            file.seek(0)

            # Convert, deserialize and store events from file in converted_events list
            converted_events = []
            for converted_event in CONVERTER.convert(file):
                converted_events.append(json.loads(converted_event))

            CONVERTOR_STATEMENTS.append((converter, converted_events))


fill_convertor_statements()


def test_each_converter_should_have_corresponding_events():
    """This test ensure that EVENTS is in sync with Converters enum.
    For each event, the CONVERTER._select_converter method should returns the
    corresponding converter.
    """

    # pylint: disable=protected-access
    for converter in Converters:
        assert converter in EVENTS
        assert len(EVENTS[converter]) == EVENT_COUNT
        for event in EVENTS[converter]:
            CONVERTER.event = event
            assert isinstance(CONVERTER._select_converter(), type(converter.value))


@pytest.mark.parametrize("convertor,statements", CONVERTOR_STATEMENTS)
def test_xapi_statements_should_be_valid(
    convertor, statements
):  # pylint: disable=unused-argument
    """Let TinCanPython validate that the converted events are valid"""

    for statement in statements:
        tincan_statement = json.loads(Statement(copy.deepcopy(statement)).to_json())
        assert statement == tincan_statement
