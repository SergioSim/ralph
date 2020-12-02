"""Tests for the base xapi converter"""

import json

import pytest

from ralph.converters.xapi.base import BaseXapiConverter
from ralph.schemas.edx.base import BaseEventSchema

from tests.fixtures.logs import EventType

SCHEMA = BaseEventSchema()
CONVERTER = BaseXapiConverter()
PLATFORM = "https://www.fun-mooc.fr"
BaseXapiConverter._platform = PLATFORM  # pylint: disable=protected-access


