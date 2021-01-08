"""Converter Base Class"""

import copy
import json
import logging
from dataclasses import dataclass
from typing import Callable

from marshmallow import Schema, ValidationError

# xAPI module logger
logger = logging.getLogger(__name__)


def nested_get(dictionary, keys):
    """Get the nested dict value by keys array"""
    if keys is None:
        return None
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


class ConversionException(Exception):
    """Raised when it's not possible to convert an event"""


@dataclass
class GetFromField:
    """Stores the source path of a field and the transformer function"""

    path: str
    transformer: Callable = lambda x: x

    def __post_init__(self):
        self.path = self.path.split(">")

    def value(self, event):
        """Call transformer function and return the transformed value"""
        field = nested_get(event, self.path)
        return self.transformer(field)


class BaseConverter:
    """Converter Base Class

    Converters define a conversion dictionary to convert from one schema to another
    """

    _schema = Schema()
    conversion_dict = {}

    def __init__(self):
        """Initialize BaseConverter"""

        self.conversion_dict = copy.deepcopy(type(self).conversion_dict)
        self.init_flat_conversion_array()

    def init_flat_conversion_array(self):
        """Initialize flat_conversion_array"""

        self.flat_conversion_array = []
        self.fill_flat_conversion_array(type(self).conversion_dict, [])

    def fill_flat_conversion_array(self, conversion_dict, path):
        """Fill flat_conversion_array with all GetFromField's"""

        for key, value in conversion_dict.items():
            if isinstance(value, dict):
                path.append(key)
                self.fill_flat_conversion_array(conversion_dict[key], path)
                path.pop()
            elif callable(value):
                nested_set(self.conversion_dict, path + [key], value())
            elif isinstance(value, GetFromField):
                self.flat_conversion_array.append((path + [key], value))

    def convert(self, event):
        """Validates, Converts and Serializes event to output_file

        Args:
            event (dict): event to validate, convert and serialize
            output_file (file-like object): destination where to serialize the event

        """
        try:
            self._schema.load(event)
        except ValidationError as err:
            logger.error("Invalid event!")
            logger.debug("Error: %s \nFor Event %s", err, event)
            return None

        for key, value in self.flat_conversion_array:
            try:
                field_value = value.value(event)
                if field_value is None:
                    nested_del(self.conversion_dict, key)
                    continue
                nested_set(self.conversion_dict, key, field_value)
            except ConversionException as err:
                logger.error("Unable to convert! %s", err)
                logger.debug("For Event %s", event)
                return None

        return json.dumps(self.conversion_dict)
