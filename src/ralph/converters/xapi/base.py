"""Base Xapi Converter"""

from tincan import Agent, Statement
from tincan.agent_account import AgentAccount

from ralph.converters.base_converter import BaseConverter, GoTo, nested_set
from ralph.schemas.edx.base import (
    BaseContextSchema,
    BaseEventSchema,
    ContextModuleSchema,
    ContextSchema,
)

from .constants import (
    XAPI_EXTENSION_ACCEPT_LANGUAGE,
    XAPI_EXTENSION_AGENT,
    XAPI_EXTENSION_COURSE_ID,
    XAPI_EXTENSION_COURSE_USER_TAGS,
    XAPI_EXTENSION_HOST,
    XAPI_EXTENSION_IP,
    XAPI_EXTENSION_ORG_ID,
    XAPI_EXTENSION_PATH,
    XAPI_EXTENSION_REFERER,
    XAPI_EXTENSION_USER_ID,
)


class BaseContextXapiConverter(BaseConverter):
    """Converts the Base Context Schema"""

    _schema = BaseContextSchema()

    course_user_tags = GoTo(
        ["context", "extensions", XAPI_EXTENSION_COURSE_USER_TAGS],
        lambda x: x if x else {},
    )
    user_id = GoTo(["context", "extensions", XAPI_EXTENSION_USER_ID])
    org_id = GoTo(["context", "extensions", XAPI_EXTENSION_ORG_ID])
    course_id = GoTo(["context", "extensions", XAPI_EXTENSION_COURSE_ID])
    path = GoTo(["context", "extensions", XAPI_EXTENSION_PATH])


class ContextModuleXapiConverter(BaseConverter):
    """Represents the context module field"""

    _schema = ContextModuleSchema()

    usage_key = GoTo(None)
    display_name = GoTo(None)


class ContextXapiConverter(BaseContextXapiConverter):
    """Context with module field. Present in Capa problems related
    events.
    """

    _schema = ContextSchema()

    module = ContextModuleXapiConverter()


class BaseXapiConverter(BaseConverter):
    """Base Xapi Converter"""

    _schema = BaseEventSchema()
    _platform = ""

    # pylint: disable=unnecessary-lambda
    username = GoTo(["actor"], lambda username: BaseXapiConverter.get_actor(username))
    ip = GoTo(
        ["context", "extensions", XAPI_EXTENSION_IP],
        lambda ip: "" if not ip else ip.exploded,
    )
    agent = GoTo(["context", "extensions", XAPI_EXTENSION_AGENT])
    host = GoTo(["context", "extensions", XAPI_EXTENSION_HOST])
    referer = GoTo(["context", "extensions", XAPI_EXTENSION_REFERER])
    accept_language = GoTo(["context", "extensions", XAPI_EXTENSION_ACCEPT_LANGUAGE])
    event_source = GoTo(None)
    context = BaseContextXapiConverter()
    time = GoTo(["timestamp"])
    page = GoTo(None)

    def convert(self, event):
        """Validates and returns the converted event

        Args:
            event (str or dict): event to convert, (when event is a dict we skip validation)

        Returns:
            None if validation fails, else the converted xApi statement str

        """

        xapi = super().convert(event)
        if not xapi:
            return None
        for go_to in self.independent_fields():
            go_to_path = go_to.path(None, event)
            if go_to_path:
                nested_set(xapi, go_to_path, go_to.value(None, event))
        return Statement(**xapi).to_json()

    @staticmethod
    def independent_fields():
        """Declare fields that stand on their own"""

        return [GoTo(["context", "platform"], BaseXapiConverter._platform)]

    @staticmethod
    def get_actor(name):
        """Returns the actor property to xapi_props"""

        if not name:
            name = "anonymous"
        account = AgentAccount(name=name, home_page=BaseXapiConverter._platform)
        return Agent(account=account)
