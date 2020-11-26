"""Entrypoint to convert events to xAPI"""

import json
import logging
from enum import Enum

from .xapi.base import BaseXapiConverter
from .xapi.server import ServerXapiConverter

# converters module logger
logger = logging.getLogger(__name__)


class Converters(Enum):
    """Stores initialized xAPI converters"""

    SERVER = ServerXapiConverter()


class XapiConverter:
    """Uses xapi converters to convert to xAPI format"""

    def __init__(self, event, platform):
        """Initialise Xapi Converter

        Args:
            event (str): event to convert
            platform (str): url of the platform to which the event belongs
        """
        BaseXapiConverter._platform = platform
        self.event = event
        try:
            self.event_dict = json.loads(event)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Xapi Converter was not able to parse input event!")
            logger.debug("For Event : %s", self.event)
            self.event_dict = None

    def convert(self):
        """Uses a matching xapi converter to validate and return the converted event"""

        if not self.event_dict:
            return None
        converter = self._select_converter()
        if converter:
            return converter.convert(self.event)
        return None

    def _select_converter(self):
        """Returns a xapi converter that matches the event"""

        event_source = self.event_dict.get("event_source", None)
        if not event_source:
            logger.info("Invalid event! Missing event_source !")
            logger.debug("For Event : %s", self.event_dict)
        if event_source == "server":
            return self._select_server_converter()
        logger.info("No matching xAPI converter found!")
        logger.debug("For Event : %s", self.event_dict)
        return None

    def _select_server_converter(self):
        """Returns a xapi server converter that matches the event"""

        if self.event_dict["event_type"] == self.event_dict["context"]["path"]:
            return Converters.SERVER.value
        return None
