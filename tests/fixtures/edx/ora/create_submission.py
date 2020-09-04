"""
openassessmentblock.create_submission event factory definition
"""
import factory
from faker import Faker

from ralph.schemas.edx.ora.create_submission import (
    CreateSubmissionEventAnswerSchema,
    CreateSubmissionEventSchema,
    CreateSubmissionSchema,
)

from ..base import _ContextFactory
from ..mixins import JSONFactoryMixin, ObjFactoryMixin
from .base_ora_event import _BaseOraEventFactory

FAKE = Faker()


class _CreateSubmissionEventAnswerFactory(factory.Factory):
    """Represents the answer field of the event field
    of an openassessementblock.create_submission event
    """

    class Meta:  # pylint: disable=missing-class-docstring
        model = CreateSubmissionEventAnswerSchema

    parts = []
    file_keys = []
    files_descriptions = []


class CreateSubmissionEventAnswerStrFactory(
    JSONFactoryMixin, _CreateSubmissionEventAnswerFactory
):
    """ Creates JSON Serialized model of the factory data """


class CreateSubmissionEventAnswerObjFactory(
    ObjFactoryMixin, _CreateSubmissionEventAnswerFactory
):
    """ Creates Deserialized model of the factory data """


class _CreateSubmissionEventFactory(factory.Factory):
    """Represents the Event Field factory of an
    openassessmentblock.create_submission
    """

    class Meta:  # pylint: disable=missing-class-docstring
        model = CreateSubmissionEventSchema

    answer = factory.Sequence(lambda n: CreateSubmissionEventAnswerObjFactory())
    attempt_number = factory.Sequence(lambda n: FAKE.random_int())
    submitted_at = factory.Sequence(lambda n: FAKE.iso8601())
    submission_uuid = factory.Sequence(lambda n: FAKE.uuid4())
    created_at = factory.Sequence(lambda n: FAKE.iso8601())


class CreateSubmissionEventStrFactory(JSONFactoryMixin, _CreateSubmissionEventFactory):
    """ Creates JSON Serialized model of the factory data """


class CreateSubmissionEventObjFactory(ObjFactoryMixin, _CreateSubmissionEventFactory):
    """ Creates Deserialized model of the factory data """


class _CreateSubmissionFactory(_BaseOraEventFactory):
    """Represents the openassessmentblock.create_submission event factory"""

    class Meta:  # pylint: disable=missing-class-docstring
        model = CreateSubmissionSchema

    event_type = "openassessmentblock.create_submission"
    event = factory.Sequence(lambda n: CreateSubmissionEventObjFactory())

    @factory.lazy_attribute
    # pylint: disable=no-member
    def context(self):
        """Returns the context field"""
        return _ContextFactory(path_tail="submit", **self.context_args)


class CreateSubmissionStrFactory(JSONFactoryMixin, _CreateSubmissionFactory):
    """ Creates JSON Serialized model of the factory data """


class CreateSubmissionObjFactory(ObjFactoryMixin, _CreateSubmissionFactory):
    """ Creates Deserialized model of the factory data """
