"""Tests for the XapiConverterSelector class"""

import importlib
import inspect
import json
from io import StringIO

import pytest

import ralph.defaults
from ralph.schemas.edx.converters.base_converter import ConversionException
from ralph.schemas.edx.converters.xapi_converter_selector import XapiConverterSelector

PLATFORM = "https://fun-mooc.fr"
CONVERTER = XapiConverterSelector(PLATFORM, False)


def convert(string_event, converter=CONVERTER):
    """Converts the data (string) using CONVERTER and returns output as a list"""
    with StringIO() as file:
        file.write(string_event)
        file.seek(0)  # Don't forget to go back to file start before reading it!
        return list(converter.convert(file))


def test_convert_with_browser_event():
    """Test that convert don't yield browser events (we don't support them for now)"""

    browser_event = json.dumps({"event_source": "browser"})
    assert convert(browser_event) == []


def test_convert_with_server_event_without_event_type():
    """Test that convert don't yield server events without event_type (they are invalid)"""

    invalid_server_event = json.dumps({"event_source": "server"})
    assert convert(invalid_server_event) == []


def test_convert_with_server_event_with_invalid_context():
    """Test that convert don't yield server events with invalid context"""

    # Missing context
    invalid_server_event = json.dumps(
        {
            "event_source": "server",
            "event_type": "/some/path",
        }
    )
    assert convert(invalid_server_event) == []

    # Context not a dict
    invalid_server_event = json.dumps(
        {"event_source": "server", "event_type": "/some/path", "context": "not a dict"}
    )
    assert convert(invalid_server_event) == []

    # Context missing path key
    invalid_server_event = json.dumps(
        {
            "event_source": "server",
            "event_type": "/some/path",
            "context": {"not_path": "/some/value"},
        }
    )
    assert convert(invalid_server_event) == []


def set_anonymization_salt_and_hash_slice_indexes(monkeypatch, salt, indexes):
    """Set the XAPI_ANONYMIZATION_SALT and XAPI_ANONYMIZATION_HASH_SLICE_INDEXES
    environment variables and reload the XapiConverterSelector module
    """

    monkeypatch.setattr(ralph.defaults, "XAPI_ANONYMIZATION_SALT", salt)
    monkeypatch.setattr(
        ralph.defaults, "XAPI_ANONYMIZATION_HASH_SLICE_INDEXES", indexes
    )
    converter_selector_module = inspect.getmodule(XapiConverterSelector)
    importlib.reload(converter_selector_module)


def test_anonymization_requires_setting_ralph_xapi_anonymization_hash_slice_indexes(
    monkeypatch,
):
    """Check that XapiConverterSelector raises Conversion exception when
    RALPH_XAPI_ANONYMIZATION_HASH_SLICE_INDEXES is not set correctly
    """

    error_message = (
        "The RALPH_XAPI_ANONYMIZATION_HASH_SLICE_INDEXES environment variable should "
        "consist of a comma separated sequence of integers"
    )
    set_anonymization_salt_and_hash_slice_indexes(monkeypatch, "", "")
    with pytest.raises(ConversionException, match=error_message):
        XapiConverterSelector(PLATFORM, True)

    set_anonymization_salt_and_hash_slice_indexes(monkeypatch, "", "ABC")
    with pytest.raises(ConversionException, match=error_message):
        XapiConverterSelector(PLATFORM, True)

    set_anonymization_salt_and_hash_slice_indexes(monkeypatch, "", "1,2,3,A,B,C")
    with pytest.raises(ConversionException, match=error_message):
        XapiConverterSelector(PLATFORM, True)

    set_anonymization_salt_and_hash_slice_indexes(monkeypatch, "", "1,2,3,")
    with pytest.raises(ConversionException, match=error_message):
        XapiConverterSelector(PLATFORM, True)

    set_anonymization_salt_and_hash_slice_indexes(monkeypatch, "", "1,2,3,10")
    try:
        XapiConverterSelector(PLATFORM, True)
    except ConversionException:
        pytest.fail(
            "No exception should be thrown when "
            "RALPH_XAPI_ANONYMIZATION_HASH_SLICE_INDEXES is set correctly"
        )


# def test_anonymization_requires_setting_ralph_xapi_anonymization_salt(monkeypatch, event):
#     """Check that XapiConverterSelector raises Conversion exception when
#     XAPI_ANONYMIZATION_SALT is not set correctly
#     """
#     error_message = (
#         "The RALPH_XAPI_ANONYMIZATION_HASH_SLICE_INDEXES environment variable should "
#         "consist of a comma separated sequence of integers"
#     )
#     set_anonymization_salt_and_hash_slice_indexes(monkeypatch, "", "1")
#     with pytest.raises(ConversionException, match=error_message):
#         server_event = json.dumps(event(EventType.SERVER))
#         print(convert(server_event, converter=XapiConverterSelector(PLATFORM, True)))
