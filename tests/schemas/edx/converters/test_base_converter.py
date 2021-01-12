"""Tests for the BaseConverter class"""

import json

import pytest
from marshmallow import Schema

from ralph.schemas.edx.base import ContextModuleSchema, ContextSchema
from ralph.schemas.edx.converters.base import (
    BaseConverter,
    GetFromField,
    nested_get,
    nested_set,
)

from tests.fixtures.logs import EventType

BASE_CONVERTER = BaseConverter()
CONTEXT_MODULE = {"display_name": "display_name_value", "usage_key": "usage_key_value"}


def test_nested_get_should_return_given_value():
    """The nested_get function should return the value when it's present in the dictionary"""

    dictionnary = {"foo": {"bar": "bar_value"}}
    assert nested_get(dictionnary, ["foo", "bar"]) == "bar_value"


def test_nested_get_should_return_null_when_value_does_not_exists():
    """The nested_get function should return null if the value is not found"""

    dictionnary = {"foo": {"bar": "bar_value"}}
    assert nested_get(dictionnary, ["foo", "bar", "baz", "qux"]) is None
    assert nested_get(dictionnary, ["foo", "not_bar"]) is None
    assert nested_get(dictionnary, ["not_foo", "bar"]) is None
    assert nested_get(dictionnary, None) is None


def test_nested_set_creating_new_fields():
    """When the fields are not present, nested_set should add them to the dictionary"""

    dictionnary = {}
    nested_set(dictionnary, ["foo", "bar"], "baz")
    assert dictionnary == {"foo": {"bar": "baz"}}


def test_nested_set_updating_fields():
    """When the fields are present, nested_set should update them"""

    dictionnary = {"foo": {"bar": "bar_value"}}
    nested_set(dictionnary, ["foo", "bar"], "baz")
    assert dictionnary == {"foo": {"bar": "baz"}}


@pytest.mark.parametrize(
    "field,args,expected_value",
    [
        ("", [], ""),
        ("some value", [], "some value"),
        ("uppercase", [lambda x: x.upper()], "UPPERCASE"),
    ],
)  # pylint: disable=too-many-arguments
def test_get_from_field(field, args, expected_value):
    """Check that for the specified arguments, we get the expected path and value"""

    get_from_field = GetFromField("some>path", *args)
    assert get_from_field.path == ["some", "path"]
    event = {"some": {"path": field}}
    assert get_from_field.value(event) == expected_value


def test_convert_with_empty_conversion_table():
    """When the conversion table is empty, convert should write an empty dictionary"""

    assert BASE_CONVERTER.convert({}) == json.dumps({})
    BASE_CONVERTER._schema = ContextModuleSchema()  # pylint: disable=protected-access
    assert BASE_CONVERTER.convert(CONTEXT_MODULE) == json.dumps({})


def test_convert_with_failing_schema_validation():
    """Check the convert function don't write to file when the event is not valid"""

    BASE_CONVERTER._schema = Schema()  # pylint: disable=protected-access
    assert BASE_CONVERTER.convert({"Not": "empty"}) is None

    BASE_CONVERTER._schema = ContextModuleSchema()  # pylint: disable=protected-access
    context_module = {}
    assert BASE_CONVERTER.convert(context_module) is None

    context_module["display_name"] = "display_name_value"
    assert BASE_CONVERTER.convert(context_module) is None


@pytest.mark.parametrize(
    "static_value",
    [
        123,
        "value",
        {"foo": "foo_value"},
        ["foo", "bar"],
    ],
)  # pylint: disable=too-many-arguments
def test_convert_with_succeeding_schema_validation_and_static_values(static_value):
    """Conversion dictionary with a static values keeps the static values"""

    BaseConverter.conversion_dict = {"static": static_value}
    base_converter = BaseConverter()
    base_converter._schema = ContextModuleSchema()  # pylint: disable=protected-access
    assert base_converter.convert(CONTEXT_MODULE) == json.dumps(
        {"static": static_value}
    )


def test_convert_with_succeeding_schema_validation_and_function_value():
    """Conversion dictionary with function values executes the function and keeps the result"""

    BaseConverter.conversion_dict = {"function": lambda: "function_output"}
    base_converter = BaseConverter()
    base_converter._schema = ContextModuleSchema()  # pylint: disable=protected-access
    assert base_converter.convert(CONTEXT_MODULE) == json.dumps(
        {"function": "function_output"}
    )


def test_convert_with_succeeding_schema_validation_and_get_from_field_value():
    """Conversion dictionary with GetFromField objects gets their value"""

    # By default we get the field from the event and put it `as it is` in the converted event
    BaseConverter.conversion_dict = {"get_from_field": GetFromField("usage_key")}
    base_converter = BaseConverter()
    base_converter._schema = ContextModuleSchema()  # pylint: disable=protected-access
    assert base_converter.convert(CONTEXT_MODULE) == json.dumps(
        {"get_from_field": "usage_key_value"}
    )

    # When we want to transform the original value we use a lambda function for that
    BaseConverter.conversion_dict["get_from_field_with_function"] = GetFromField(
        "usage_key", lambda usage_key: usage_key.upper()
    )
    base_converter = BaseConverter()
    base_converter._schema = ContextModuleSchema()  # pylint: disable=protected-access
    assert base_converter.convert(CONTEXT_MODULE) == json.dumps(
        {
            "get_from_field": "usage_key_value",
            "get_from_field_with_function": "USAGE_KEY_VALUE",
        }
    )


def test_convert_with_nested_fields(event):
    """Check the convert function for a schema with nested fields"""

    # Create the context dictionary and conversion_dict
    context = event(EventType.SERVER)["context"]
    context["module"] = CONTEXT_MODULE
    course_id = context["course_id"]
    context[
        "path"
    ] = f"/courses/{course_id}/xblock/{CONTEXT_MODULE['usage_key']}/handler/"
    BaseConverter.conversion_dict = {
        "new_path": GetFromField("path", lambda path: path.upper()),
        "nested": {
            "new_usage_key": GetFromField("module>usage_key"),
            "function": lambda: 1 + 1,
            "nested": {
                "new_display_name": GetFromField("module>display_name"),
                "static": "value",
            },
        },
    }
    # Create the converter and run test
    base_converter = BaseConverter()
    base_converter._schema = ContextSchema()  # pylint: disable=protected-access
    assert base_converter.convert(context) == json.dumps(
        {
            "new_path": context["path"].upper(),
            "nested": {
                "new_usage_key": context["module"]["usage_key"],
                "function": 2,
                "nested": {
                    "new_display_name": context["module"]["display_name"],
                    "static": "value",
                },
            },
        }
    )
