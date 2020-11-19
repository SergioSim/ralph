"""Server event xAPI Converter"""

from tincan import Activity, ActivityDefinition, LanguageMap

from ralph.schemas.edx.server import ServerEventSchema

from .base import BaseXapiConverter
from .constants import (
    EN,
    HOME_PAGE,
    PAGE,
    VIEWED,
    XAPI_ACTIVITY_PAGE,
    XAPI_EXTENSION_REQUEST,
    XAPI_VERB_VIEWED,
)


class ServerXapiConverter(ServerEventSchema, BaseXapiConverter):
    """Converts a common edx server event to xAPI
    See ServerEventSchema for info about the Edx server event
    Example Statement: John viewed https://www.fun-mooc.fr/ Web page
    """

    def get_verb_kwargs(self):  # pylint: disable=no-self-use
        """Returns tincan.Verb kwargs for the xapi_event"""

        return {"id": XAPI_VERB_VIEWED, "display": LanguageMap({EN: VIEWED})}

    def get_object(self):
        """Returns the object property to the xapi_event"""

        definition = ActivityDefinition(
            type=XAPI_ACTIVITY_PAGE, name=LanguageMap({EN: PAGE})
        )
        viewed_page = HOME_PAGE + self.edx_event["event_type"]
        return Activity(id=viewed_page, definition=definition)

    def update_extensions(self):
        """Add request extension to context extensions"""

        return {XAPI_EXTENSION_REQUEST: self.edx_event["event"]}
