"""Server event xAPI Converter"""
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
from ralph.schemas.edx.converters.base_converter import GetFromField
from ralph.schemas.edx.server_event import ServerEventSchema

from ..base_converter import ConversionException
from . import constants as const
from .base import BaseXapiConverter


class ServerEventToXapi(BaseXapiConverter):
    """Converts a common edX server event to xAPI
    See ServerEventSchema for info about the edX server event
    Example Statement: John viewed https://www.fun-mooc.fr/ Web page
    """

    _schema = ServerEventSchema()

    conversion_dict = {
        "version": const.VERSION,
        "actor": {
            "account": {
                "name": GetFromField(
                    "context>user_id",
                    # pylint: disable=unnecessary-lambda
                    lambda user_id: ServerEventToXapi.transform_user_id(user_id),
                ),
                "homePage": lambda: BaseXapiConverter._platform,
            },
            "objectType": "Agent",
        },
        "verb": {"id": const.XAPI_VERB_VIEWED, "display": {"en": const.VIEWED}},
        "object": {
            "id": GetFromField(
                "event_type",
                lambda event_type: BaseXapiConverter._platform + event_type,
            ),
            "definition": {
                "type": const.XAPI_ACTIVITY_PAGE,
                "name": {"en": const.PAGE},
            },
            "objectType": "Activity",
        },
        "context": {
            "platform": lambda: BaseXapiConverter._platform,
            "extensions": {
                const.XAPI_EXTENSION_ACCEPT_LANGUAGE: GetFromField("accept_language"),
                const.XAPI_EXTENSION_AGENT: GetFromField("agent"),
                const.XAPI_EXTENSION_COURSE_ID: GetFromField("context>course_id"),
                const.XAPI_EXTENSION_COURSE_USER_TAGS: GetFromField(
                    "context>course_user_tags",
                    lambda course_user_tags: course_user_tags
                    if course_user_tags
                    else None,
                ),
                const.XAPI_EXTENSION_HOST: GetFromField("host"),
                const.XAPI_EXTENSION_IP: GetFromField("ip"),
                const.XAPI_EXTENSION_ORG_ID: GetFromField("context>org_id"),
                const.XAPI_EXTENSION_PATH: GetFromField("context>path"),
                const.XAPI_EXTENSION_REQUEST: GetFromField("event"),
            },
        },
        "timestamp": GetFromField("time"),
    }

    @staticmethod
    def transform_user_id(user_id):
        """Transforms edX context>user_id for xAPI actor>account>name"""
        if not user_id:
            return "student"
        if not BaseXapiConverter._anonymize:
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
        return "".join(
            [
                base64_user_id[x]
                for x in BaseXapiConverter._anonymization_hash_slice_indexes
            ]
        )
