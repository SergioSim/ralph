"""Entrypoint to convert events to xAPI"""

import json
import logging
from enum import Enum

from ralph.defaults import XAPI_ANONYMIZATION_HASH_SLICE_INDEXES
from ralph.schemas.edx.converters.base import ConversionException

from .xapi.base import BaseXapiConverter
from .xapi.server_event_to_xapi import ServerEventToXapi

# converters module logger
logger = logging.getLogger(__name__)


class Converters(Enum):
    """Stores initialized xAPI converters"""

    SERVER = ServerEventToXapi()


class XapiConverterSelector:
    """Select a matching xAPI converter to convert to xAPI format"""

    def __init__(self, platform, anonymize):
        """Initialise XapiConverterSelector

        Args:
            platform (str): URL of the platform to which the event belongs
            anonymize (bool): when True - anonymize xAPI statements

        """

        self.event = None
        BaseXapiConverter._platform = platform
        BaseXapiConverter._anonymize = anonymize
        if anonymize:
            BaseXapiConverter._anonymization_hash_slice_indexes = (
                self._get_anonymization_hash_slice_indexes()
            )

        for converter in Converters:
            converter.value.init_flat_conversion_array()

    def convert(self, input_file):
        """Uses a matching xAPI converter to validate and return the converted event"""

        for event in input_file:
            try:
                self.event = json.loads(event)
            except (json.JSONDecodeError, TypeError):
                self._log_error("Invalid event! Not parsable JSON!")
                continue
            if not isinstance(self.event, dict):
                self._log_error("Invalid event! Not a dictionary!")
                continue
            converter = self._select_converter()
            if not converter:
                continue
            yield converter.convert(self.event)

    def _select_converter(self):
        """Return a xAPI converter that matches the event"""

        event_source = self.event.get("event_source", None)
        if not event_source:
            self._log_error("Invalid event! Missing event_source!")
            return None
        if event_source == "server":
            return self._select_server_converter()
        self._log_error("No matching xAPI converter found!")
        return None

    def _select_server_converter(self):
        """Return a xAPI server converter that matches the event"""

        event_type = self.event.get("event_type", None)
        context = self.event.get("context", None)
        if not event_type or not context:
            self._log_error("Invalid event! Missing event_type or context!")
            return None
        if not isinstance(context, dict):
            self._log_error("Invalid event! Context not a dictionary!")
            return None
        if event_type == context.get("path", None):
            return Converters.SERVER.value
        self._log_error("No matching server xAPI converter found!")
        return None

    @staticmethod
    def _get_anonymization_hash_slice_indexes():
        anonymization_hash_slice_indexes = []
        for index in XAPI_ANONYMIZATION_HASH_SLICE_INDEXES.split(","):
            try:
                anonymization_hash_slice_indexes.append(int(index))
            except ValueError as err:
                raise ConversionException(
                    "The RALPH_XAPI_ANONYMIZATION_HASH_SLICE_INDEXES environment variable "
                    "should consist of a comma separated sequence of integers"
                ) from err
        return anonymization_hash_slice_indexes

    def _log_error(self, message):
        logger.error(message)
        logger.debug("For Event : %s", self.event)
