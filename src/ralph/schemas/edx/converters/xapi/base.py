"""Base xAPI Converter"""

import base64

from argon2.exceptions import HashingError
from argon2.low_level import Type, hash_secret_raw

from ralph.defaults import (
    XAPI_ANONYMIZATION_HASH_LENGTH,
    XAPI_ANONYMIZATION_MEMORY_COST,
    XAPI_ANONYMIZATION_PARALLELISM,
    XAPI_ANONYMIZATION_SALT,
    XAPI_ANONYMIZATION_TIME_COST,
)
from ralph.exceptions import ConversionException
from ralph.schemas.edx.converters.base import BaseConverter, GetFromField

from .constants import (
    VERSION,
    XAPI_EXTENSION_ACCEPT_LANGUAGE,
    XAPI_EXTENSION_AGENT,
    XAPI_EXTENSION_COURSE_ID,
    XAPI_EXTENSION_COURSE_USER_TAGS,
    XAPI_EXTENSION_HOST,
    XAPI_EXTENSION_IP,
    XAPI_EXTENSION_ORG_ID,
    XAPI_EXTENSION_PATH,
    XAPI_EXTENSION_REQUEST,
)


class BaseXapiConverter(BaseConverter):
    """Base xAPI Converter"""

    def __init__(self, platform, anonymize, anonymization_hash_indexes):
        """Initialize BaseXapiConverter"""
        self.platform = platform
        self.anonymize = anonymize
        self.anonymization_hash_indexes = anonymization_hash_indexes
        super().__init__()

    def get_conversion_dictionary(self):
        """Returns a conversion dictionary used for conversion."""
        return {
            "actor": self.actor,
            "context": self.context,
            "object": self.object,
            "verb": self.verb,
            "version": VERSION,
            "timestamp": GetFromField("time"),
        }

    @property
    def actor(self):
        """Get statement actor from event (required)"""
        return {
            "account": {
                "name": GetFromField(
                    "context>user_id",
                    # pylint: disable=unnecessary-lambda
                    lambda user_id: self.transform_user_id(user_id),
                ),
                "homePage": self.platform,
            },
            "objectType": "Agent",
        }

    @property
    def context(self):
        """Get statement context from event"""
        return {
            "platform": self.platform,
            "extensions": {
                XAPI_EXTENSION_ACCEPT_LANGUAGE: GetFromField("accept_language"),
                XAPI_EXTENSION_AGENT: GetFromField("agent"),
                XAPI_EXTENSION_COURSE_ID: GetFromField("context>course_id"),
                XAPI_EXTENSION_COURSE_USER_TAGS: GetFromField(
                    "context>course_user_tags",
                    lambda course_user_tags: course_user_tags
                    if course_user_tags
                    else None,
                ),
                XAPI_EXTENSION_HOST: GetFromField("host"),
                XAPI_EXTENSION_IP: GetFromField("ip"),
                XAPI_EXTENSION_ORG_ID: GetFromField("context>org_id"),
                XAPI_EXTENSION_PATH: GetFromField("context>path"),
                XAPI_EXTENSION_REQUEST: GetFromField("event"),
            },
        }

    @property
    def object(self):
        """Get statement object from event (required)"""
        raise NotImplementedError(
            f"{self.__class__.__name__} xAPI statement class should implement the object property"
        )

    @property
    def verb(self):
        """Get statement verb from event (required)"""
        raise NotImplementedError(
            f"{self.__class__.__name__} xAPI statement class should implement the verb property"
        )

    def transform_user_id(self, user_id):
        """Transforms edX context>user_id for xAPI actor>account>name"""

        if not user_id:
            return "student"
        if not self.anonymize:
            return str(user_id)
        try:
            hashed_user_id = hash_secret_raw(
                bytes(str(user_id), "utf-8"),
                bytes(XAPI_ANONYMIZATION_SALT, "utf-8"),
                time_cost=XAPI_ANONYMIZATION_TIME_COST,
                memory_cost=XAPI_ANONYMIZATION_MEMORY_COST,
                parallelism=XAPI_ANONYMIZATION_PARALLELISM,
                hash_len=XAPI_ANONYMIZATION_HASH_LENGTH,
                type=Type.D,
            )
        except HashingError as err:
            raise ConversionException(str(err)) from err
        missing_padding = len(hashed_user_id) % 4
        if missing_padding:
            hashed_user_id += b"=" * (4 - missing_padding)
        base64_user_id = base64.b64encode(hashed_user_id).decode("utf-8")
        return "".join([base64_user_id[x] for x in self.anonymization_hash_indexes])
