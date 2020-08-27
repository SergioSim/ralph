"""
base event factory for ora (openassessment) events
"""
import factory
from faker import Faker

from ralph.schemas.edx.ora.base_ora_event import BaseOraEventSchema

from ..base import _BaseEventFactory
from ..mixins import JSONFactoryMixin, ObjFactoryMixin

FAKE = Faker()


class _BaseOraEventFactory(_BaseEventFactory):
    """Represents the base event factory for ora events"""

    class Meta:  # pylint: disable=missing-class-docstring
        model = BaseOraEventSchema

    username = factory.Sequence(lambda n: FAKE.profile().get("username"))
    page = "x_module"


class BaseOraEventStrFactory(JSONFactoryMixin, _BaseOraEventFactory):
    """ Creates JSON Serialized model of the factory data """


class BaseOraEventObjFactory(ObjFactoryMixin, _BaseOraEventFactory):
    """ Creates Deserialized model of the factory data """
