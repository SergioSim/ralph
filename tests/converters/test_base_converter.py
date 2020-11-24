"""Tests for the BaseConverter class"""

import pytest

from ralph.converters.base_converter import (
    BaseConverter,
    GoTo,
    KwargPath,
    Link,
    nested_get,
    nested_set,
)
from ralph.schemas.edx.base import ContextModuleSchema, ContextSchema

DICTIONNARY = {"foo": {"bar": "baz"}, "qux": "qux_value", "quux": "quux"}


def test_nested_get_should_return_given_value():
    """The nested_get function should return the value when it's present in the dictionnary"""
    assert nested_get(DICTIONNARY, ["foo", "bar"]) == "baz"


def test_nested_get_should_return_null_when_value_does_not_exists():
    """The nested_get function should return null if the value is not found"""
    assert nested_get(DICTIONNARY, ["foo", "bar", "baz", "qux"]) is None
    assert nested_get(DICTIONNARY, ["foo", "not_bar"]) is None
    assert nested_get(DICTIONNARY, ["not_foo", "bar"]) is None
    assert nested_get(DICTIONNARY, None) is None


def test_nested_set_creating_new_fields():
    """When the fields are not present, nested_set should add them to the dictionnary"""
    dictionnary = {}
    nested_set(dictionnary, ["foo", "bar"], "baz")
    assert dictionnary == {"foo": {"bar": "baz"}}


def test_nested_set_updating_fields():
    """When the fields are present, nested_set should update them"""
    dictionnary = {"foo": {"bar": "not_baz"}}
    nested_set(dictionnary, ["foo", "bar"], "baz")
    assert dictionnary == {"foo": {"bar": "baz"}}


def test_link_with_one_existing_path():
    """Check when the path in the Link is present in the dictionnary
    then the value of the key word argument should be the field value
    """
    link = Link(
        [KwargPath("bar_value", ["foo", "bar"])], lambda x, bar_value: (x, bar_value)
    )
    assert link.get("qux_value", DICTIONNARY) == ("qux_value", "baz")


def test_link_with_two_existing_paths():
    """Check when the paths in the Link is present in the dictionnary
    then the values of the key word arguments should be the fields values
    """
    link = Link(
        [
            KwargPath("bar_value", ["foo", "bar"]),
            KwargPath("quux_value", ["quux"]),
        ],
        lambda x, bar_value, quux_value: (x, bar_value, quux_value),
    )
    assert link.get("qux_value", DICTIONNARY) == ("qux_value", "baz", "quux")


def test_link_with_one_non_existing_path_should_use_the_value_none():
    """Check when the path in the Link is not present in the dictionnary
    then the value of the key word argument should be none
    """
    link = Link(
        [KwargPath("not_existing_value", ["foo", "bar", "baz", "qux"])],
        lambda x, not_existing_value: (x, not_existing_value),
    )
    assert link.get("qux_value", DICTIONNARY) == ("qux_value", None)


@pytest.mark.parametrize(
    "path_field,path,expected_path",
    [
        ("", ["foo"], ["foo"]),
        ("", ["foo", "bar"], ["foo", "bar"]),
        ("", lambda x: x, ""),
        ("some value", lambda x: x, "some value"),
        (
            "some value",
            Link(
                [KwargPath("bar_value", ["foo", "bar"])],
                lambda x, bar_value: [x, bar_value],
            ),
            ["some value", "baz"],
        ),
    ],
)
@pytest.mark.parametrize(
    "value_field,value_arg,expected_value",
    [
        ("", ["static_value"], "static_value"),
        ("", [123], 123),
        ("", [{"foo": "bar"}], {"foo": "bar"}),
        ("", [], ""),
        ("some value", [], "some value"),
        (
            "some value",
            [
                Link(
                    [KwargPath("bar_value", ["foo", "bar"])],
                    lambda x, bar_value: (x, bar_value),
                )
            ],
            ("some value", "baz"),
        ),
    ],
)  # pylint: disable=too-many-arguments
def test_go_to(path_field, path, expected_path, value_field, value_arg, expected_value):
    """Check that for the specified kwargs, value we get the expected path and value"""
    args = [path] + value_arg
    go_to = GoTo(*args)
    assert go_to.path(path_field, DICTIONNARY) == expected_path
    assert go_to.value(value_field, DICTIONNARY) == expected_value


def test_convert_without_nesting():
    """Check the convert function for a schmea without nested fields"""
    converter = BaseConverter()
    assert converter.convert(DICTIONNARY) == {}

    converter._schema = ContextModuleSchema()  # pylint: disable=protected-access
    # When the _schema contains more fields than we have defined, Attribute error is raised
    with pytest.raises(
        AttributeError,
        match="'BaseConverter' object has no attribute '(display_name|usage_key)'",
    ):
        assert converter.convert(DICTIONNARY) == {}

    converter.display_name = GoTo(["foo"])
    # Now only usage_key is missing
    with pytest.raises(
        AttributeError, match="'BaseConverter' object has no attribute 'usage_key'"
    ):
        assert converter.convert(DICTIONNARY) == {}
    converter.usage_key = GoTo(["bar"])

    # When a field is not found the default is None
    assert converter.convert(DICTIONNARY) == {"bar": None, "foo": None}

    # We should be able to skip a field
    converter.usage_key = GoTo(None)
    assert converter.convert(DICTIONNARY) == {"foo": None}

    # We may indicate a static value for the field (field not present)
    converter.display_name = GoTo(["foo"], "static_value")
    assert converter.convert(DICTIONNARY) == {"foo": "static_value"}

    # When a field is found the default is it's value
    converter.display_name = GoTo(["foo"])
    DICTIONNARY["display_name"] = "display_name"
    assert converter.convert(DICTIONNARY) == {"foo": "display_name"}

    # We may indicate a static value for the field (field present)
    converter.display_name = GoTo(["foo"], "static_value")
    assert converter.convert(DICTIONNARY) == {"foo": "static_value"}

    # We may apply a transformation to the field
    converter.display_name = GoTo(["foo"], lambda x: x.upper())
    assert converter.convert(DICTIONNARY) == {"foo": "DISPLAY_NAME"}

    # We may apply a transformation to the field with the help of other fields
    converter.display_name = GoTo(
        ["foo"],
        Link(
            [KwargPath("bar_value", ["foo", "bar"]), KwargPath("quux_value", ["quux"])],
            lambda x, bar_value, quux_value: (x, bar_value, quux_value),
        ),
    )
    assert converter.convert(DICTIONNARY) == {"foo": ("display_name", "baz", "quux")}

    # We may alter the destination path depending on the field value
    converter.display_name = GoTo(lambda x: ["baz"] if x == "change" else ["foo"])
    assert converter.convert(DICTIONNARY) == {"foo": "display_name"}
    DICTIONNARY["display_name"] = "change"
    assert converter.convert(DICTIONNARY) == {"baz": "change"}

    # We may alter the destination path depending on other fields values
    converter.display_name = GoTo(
        Link(
            [KwargPath("bar_value", ["foo", "bar"]), KwargPath("quux_value", ["quux"])],
            lambda x, bar_value, quux_value: [x, bar_value, quux_value],
        )
    )
    DICTIONNARY["display_name"] = "display_name"
    assert converter.convert(DICTIONNARY) == {
        "display_name": {"baz": {"quux": "display_name"}}
    }
    DICTIONNARY["foo"]["bar"] = "change"
    assert converter.convert(DICTIONNARY) == {
        "display_name": {"change": {"quux": "display_name"}}
    }


def test_convert_with_nesting():
    """Check the convert function for a schmea with nested fields"""
    converter = BaseConverter()
    converter._schema = ContextSchema()  # pylint: disable=protected-access
    converter.course_user_tags = GoTo(None)
    converter.user_id = GoTo(None)
    converter.org_id = GoTo(None)
    converter.course_id = GoTo(None)
    converter.path = GoTo(None)
    # When the _schema contains more fields than we have defined, Attribute error is raised
    with pytest.raises(
        AttributeError, match="'BaseConverter' object has no attribute '(module)'"
    ):
        assert converter.convert(DICTIONNARY) == {}

    # When the _schema of the nested converter contains more fields than we have defined,
    # Attribute error is raised
    nested_converter = BaseConverter()
    nested_converter._schema = ContextModuleSchema()  # pylint: disable=protected-access
    converter.module = nested_converter
    with pytest.raises(
        AttributeError,
        match="'BaseConverter' object has no attribute '(display_name|usage_key)'",
    ):
        assert converter.convert(DICTIONNARY) == {}

    # Nested fields should recieve their corresponfing (nested) values
    nested_converter.display_name = GoTo(None)
    nested_converter.usage_key = GoTo(["foo"])
    DICTIONNARY["usage_key"] = "usage_key"  # field is not nested!
    assert converter.convert(DICTIONNARY) == {"foo": None}
    del DICTIONNARY["usage_key"]
    nested_set(DICTIONNARY, ["module", "usage_key"], "usage_key")
    assert converter.convert(DICTIONNARY) == {"foo": "usage_key"}
