"""Server event xAPI Converter"""

from ralph.schemas.edx.converters.base_converter import GetFromField
from ralph.schemas.edx.server_event import ServerEventSchema

from . import constants as const
from .base import BaseXapiConverter


class ServerEventToXapi(BaseXapiConverter):
    """Converts a common edx server event to xAPI
    See ServerEventSchema for info about the Edx server event
    Example Statement: John viewed https://www.fun-mooc.fr/ Web page
    """

    _schema = ServerEventSchema()

    conversion_dict = {
        "version": const.VERSION,
        "actor": {
            "account": {
                "name": GetFromField(
                    "context>user_id",
                    lambda user_id: str(user_id) if user_id else "student",
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
                    else {},
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
