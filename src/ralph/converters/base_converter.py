"""Converter Base Class"""

import logging
from dataclasses import dataclass
from typing import Callable, List, Union

from marshmallow import Schema, ValidationError

# xapi module logger
logger = logging.getLogger(__name__)


def nested_get(dictionary, keys):
    """Return the nested value by keys array"""
    if not keys:
        return None
    for key in keys[:-1]:
        if not isinstance(dictionary, dict):
            return None
        dictionary = dictionary.get(key, None)
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(keys[-1], None)


def nested_set(dictionary, keys, value):
    """Set the nested dict value by keys array"""
    for key in keys[:-1]:
        dictionary = dictionary.setdefault(key, {})
    dictionary[keys[-1]] = value


@dataclass
class KwargPath:
    """Stores a key word argument and a path to retrieve it's value"""

    kwarg: str
    path: list


@dataclass
class Link:
    """Stores a function and it's key word arguments

    It is used to define transormations that require multiple input fields
    """

    kwarg_paths: List[KwargPath]
    function: Callable

    def get(self, field, event):
        """Calls the function with it's key word arguments and returns the obtained value"""
        kwargs = {}
        for kwarg_path in self.kwarg_paths:
            kwargs[kwarg_path.kwarg] = nested_get(event, kwarg_path.path)
        return self.function(field, **kwargs)


@dataclass
class GoTo:
    """Stores the destination path of a field and the applied transformations"""

    _path: Union[None, List[str], Callable, Link]
    _value: Union[int, str, list, dict, Callable, Link] = lambda x: x

    def path(self, field, event):
        """Return the destination path of the field"""
        return self._get(self._path, field, event)

    def value(self, field, event):
        """Return the value of the field"""
        return self._get(self._value, field, event)

    @staticmethod
    def _get(value, field, event):
        """Call transformation function (if defined) and return the (transformed) value"""
        if isinstance(value, Link):
            return value.get(field, event)
        if callable(value):
            return value(field)
        return value


class BaseConverter:
    """Converter Base Class

    Converters define for each field present in their _schema a GoTo mapping
    which express the destination(s) path(s) and transformation(s) to apply to the field
    """

    _schema = Schema()

    def convert(self, event):
        """Validates and returns the converted event

        Args:
            event (dict): event to validate and convert

        Returns:
            None if validation fails, else the converted event (dict)

        """
        try:
            validated_event = self._schema.load(event)
        except ValidationError as err:
            logger.info("Invalid event!")
            logger.debug("Error: %s \nFor Event %s", err, event)
            return None
        return self._convert(self, validated_event, {}, [])

    @staticmethod
    def _convert(converter, event, result, path):
        # pylint: disable=protected-access
        for key in converter._schema.fields:
            go_to = getattr(converter, key)
            if isinstance(go_to, BaseConverter):
                path.append(key)
                converter._convert(go_to, event, result, path)
                path.pop()
            if isinstance(go_to, GoTo):
                field = nested_get(event, path + [key])
                go_to_path = go_to.path(field, event)
                if go_to_path:
                    nested_set(result, go_to_path, go_to.value(field, event))
        return result
