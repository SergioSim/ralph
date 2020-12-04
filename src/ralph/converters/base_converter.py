"""Converter Base Class"""

import copy
import logging
from dataclasses import dataclass
from functools import reduce
import json
from typing import Callable, Union

from marshmallow import Schema, ValidationError

# xapi module logger
logger = logging.getLogger(__name__)


def nested_get(dictionary, keys):
    for key in keys:
        try:
            dictionary = dictionary[key]
        except (KeyError, TypeError):
            return None
    return dictionary


def nested_set(dictionary, keys, value):
    """Set the nested dict value by keys array"""
    for key in keys[:-1]:
        dictionary = dictionary.setdefault(key, {})
    dictionary[keys[-1]] = value


def nested_del(dictionary, keys):
    """Remove the nested dict key by keys array"""
    for key in keys[:-1]:
        if key not in dictionary:
            return
        dictionary = dictionary[key]
    if keys[-1] not in dictionary:
        return
    del dictionary[keys[-1]]


@dataclass
class GetFromField:
    """Stores the source path of a field and the applied transformations"""

    path: Union[None, str]
    _value: Union[int, str, list, dict, Callable] = lambda x: x

    def value(self, field):
        """Call transformation function (if defined) and return the (transformed) value"""
        if callable(self._value):
            return self._value(field)
        return self._value


class BaseConverter:
    """Converter Base Class

    Converters define a conversion dictionnary to convert from one json schema to another
    """

    _schema = Schema()
    conversion_dict = {}

    def __init__(self):
        """Initialize Base Converter"""

        self.conversion_dict = copy.deepcopy(type(self).conversion_dict)
        self.flat_conversion_array = []
        self.fill_flat_conversion_array(self.conversion_dict, [])


    def fill_flat_conversion_array(self, conversion_dict, path):
        """Create an array containg all conversion rules"""
        for key, value in conversion_dict.items():
            if isinstance(value, dict):
                path.append(key)
                self.fill_flat_conversion_array(conversion_dict[key], path)
                path.pop()
            elif callable(value):
                self.flat_conversion_array.append((path + [key], value))
            elif isinstance(value, GetFromField):
                value.path = value.path.split(">")
                self.flat_conversion_array.append((path + [key], value))


    def convert(self, event):
        """Validates and returns the converted event

        Args:
            event (dict): event to validate and convert

        Returns:
            None if validation fails, else the converted event (dict)

        """
        # try:
        #     valid_event = self._schema.load(event)
        # except ValidationError as err:
        #     logger.info("Invalid event!")
        #     logger.debug("Error: %s \nFor Event %s", err, event)
        #     return None
        valid_event = event
        for key, value in self.flat_conversion_array:
            if callable(value):
                nested_set(self.conversion_dict, key, value())
            elif isinstance(value, GetFromField):
                field = value.value(nested_get(valid_event, value.path))
                if field is None:
                    nested_del(self.conversion_dict, key)
                else:
                    nested_set(self.conversion_dict, key, field)
        return json.dumps(self.conversion_dict)

    def _convert(self, event, conversion_dict, path):
        """Walk recursively through the conversion_dict,
        replacing GetFromField's and lambda's with their values from the event
        """
        for key, value in conversion_dict.items():
            if isinstance(value, dict):
                path.append(key)
                self._convert(event, conversion_dict[key], path)
                path.pop()
            elif callable(value):
                nested_set(self.conversion_dict, path + [key], value())
            elif isinstance(value, GetFromField):
                field = nested_get(event, value.path)
                new_field_value = value.value(field)
                if new_field_value is None:
                    nested_del(self.conversion_dict, path + [key])
                else:
                    nested_set(self.conversion_dict, path + [key], value.value(field))
