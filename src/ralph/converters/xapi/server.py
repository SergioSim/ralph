"""Server event xAPI Converter"""

from tincan import Activity, ActivityDefinition, LanguageMap, Verb

from ralph.converters.base_converter import GoTo
from ralph.schemas.edx.server import ServerEventSchema

from .base import BaseXapiConverter
from .constants import (
    EN,
    PAGE,
    VIEWED,
    XAPI_ACTIVITY_PAGE,
    XAPI_EXTENSION_REQUEST,
    XAPI_VERB_VIEWED,
)


class ServerXapiConverter(BaseXapiConverter):
    """Converts a common edx server event to xAPI
    See ServerEventSchema for info about the Edx server event
    Example Statement: John viewed https://www.fun-mooc.fr/ Web page
    """

    _schema = ServerEventSchema()

    # pylint: disable=unnecessary-lambda
    event_type = GoTo(
        ["object"], lambda event_type: ServerXapiConverter.get_object(event_type)
    )
    event = GoTo(["context", "extensions", XAPI_EXTENSION_REQUEST])

    @staticmethod
    def get_object(event_type):
        """Returns the object property to the xapi_event"""

        definition = ActivityDefinition(
            type=XAPI_ACTIVITY_PAGE, name=LanguageMap({EN: PAGE})
        )
        viewed_page = BaseXapiConverter._platform + event_type
        return Activity(id=viewed_page, definition=definition)

    @staticmethod
    def independent_fields():
        """Declare fields that stand on their own"""

        fields = BaseXapiConverter.independent_fields()
        return fields + [
            GoTo(["verb"], Verb(id=XAPI_VERB_VIEWED, display=LanguageMap({EN: VIEWED})))
        ]
