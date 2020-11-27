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


class XapiConverterSelector:
    """Select a matching xAPI converter to convert to xAPI format"""

    def __init__(self, event, platform):
        """Initialise Xapi Converter Selector

        Args:
            event (str): event to validate and convert
            platform (str): url of the platform to which the event belongs

        """

        BaseXapiConverter._platform = platform
        try:
            self.event = json.loads(event)
        except (json.JSONDecodeError, TypeError):
            self.event = None
            self._log_error("Invalid event! Not json parsable!")

    def convert(self):
        """Uses a matching xapi converter to validate and return the converted event"""

        if not self.event:
            return None
        converter = self._select_converter()
        if not converter:
            return None
        return converter.convert(self.event)

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
        if event_type == context.get("path", None):
            return Converters.SERVER.value
        return None

    def _log_error(self, message):
        logger.info(message)
        logger.debug("For Event : %s", self.event)
