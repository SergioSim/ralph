"""Base Xapi Converter"""

import json

from marshmallow import post_dump, pre_dump
from tincan import Agent, Context, Statement, Verb
from tincan.agent_account import AgentAccount

from ralph.schemas.edx.base import BaseEventSchema

from .constants import (
    HOME_PAGE,
    XAPI_EXTENSION_ACCEPT_LANGUAGE,
    XAPI_EXTENSION_AGENT,
    XAPI_EXTENSION_COURSE_ID,
    XAPI_EXTENSION_COURSE_USER_TAGS,
    XAPI_EXTENSION_HOST,
    XAPI_EXTENSION_IP,
    XAPI_EXTENSION_ORG_ID,
    XAPI_EXTENSION_REFERER,
    XAPI_EXTENSION_USER_ID,
)


class BaseXapiConverter(BaseEventSchema):
    """Base Xapi Converter
    Loads a string or json edx event, BaseEventSchema validates input
    Dumps a string or json xapi event, tincan package validates output
    """

    def __init__(self, *args, **kwargs):
        """Init edx_event, xapi_props and xapi_statement
        edx_event is the validated deserialized edx event
        xapi_props is populated with xapi properties (actor, verb, object, etc.)
        xapi_props are used to create the converted xapi event (statement)
        """

        super().__init__(*args, **kwargs)
        self.edx_event = {}
        self.xapi_props = {}

    @pre_dump
    def convert(self, edx_event, many):  # pylint: disable=unused-argument
        """Convert edx event to xApi"""

        self.edx_event = edx_event
        self.xapi_props = {}
        self.add_required_properties()
        self.add_optional_properties()

    @post_dump
    def get_xapi_statement(self, data, many):  # pylint: disable=unused-argument
        """Returns the xApi Statement"""

        return json.loads(Statement(**self.xapi_props).to_json())

    def add_required_properties(self):
        """Add the required actor, verb, object properies to xapi_props"""

        self.xapi_props["actor"] = self.get_actor()
        self.xapi_props["verb"] = Verb(**self.get_verb_kwargs())
        self.xapi_props["object"] = self.get_object()

    def add_optional_properties(self):
        """Add the optional result, context, timestamp properies to xapi_props"""

        self.add_optional_property("result", self.get_result())
        self.add_optional_property("context", self.get_context())
        self.add_optional_property("timestamp", self.get_timestamp())

    def add_optional_property(self, name, value):
        """Add an optional property by given name if the value is not None"""

        if value is not None:
            self.xapi_props[name] = value

    def get_actor(self):
        """Returns the actor property to xapi_props"""

        name = self.edx_event["username"]
        if not name:
            name = "anonymous"
        account = AgentAccount(name=name, home_page=HOME_PAGE)
        return Agent(account=account)

    def get_verb_kwargs(self):
        """Returns tincan.Verb kwargs as a dict for xapi_props
        should contain id and display key value pairs
        """

        raise NotImplementedError("get_verb_kwargs should be implemented")

    def get_object(self):
        """Returns the object property for xapi_props
        it might be a tincan Activity, Agent, SubStatement or StatementRef
        """

        raise NotImplementedError("get_object should be implemented")

    def get_result(self):  # pylint: disable=no-self-use
        """Returns the result property for xapi_props"""

        return None

    def get_context(self):
        """Returns the context property for xapi_props"""

        return Context(
            extensions=self.get_common_context_extensions(), platform=HOME_PAGE
        )

    def get_common_context_extensions(self):
        """Returns the extensions property for xapi_props context"""

        context = self.edx_event["context"]
        event_ip = self.edx_event["ip"]
        if event_ip:
            event_ip = event_ip.exploded
        extensions = {
            XAPI_EXTENSION_ACCEPT_LANGUAGE: self.edx_event["accept_language"],
            XAPI_EXTENSION_AGENT: self.edx_event["agent"],
            XAPI_EXTENSION_COURSE_ID: context["course_id"],
            XAPI_EXTENSION_COURSE_USER_TAGS: context.get("course_user_tags", {}),
            XAPI_EXTENSION_HOST: self.edx_event["host"],
            XAPI_EXTENSION_IP: event_ip,
            XAPI_EXTENSION_ORG_ID: context["org_id"],
            XAPI_EXTENSION_REFERER: self.edx_event["referer"],
            XAPI_EXTENSION_USER_ID: context["user_id"],
        }
        extensions.update(self.update_extensions())
        return extensions

    def update_extensions(self):  # pylint: disable=no-self-use
        """Returns a dictionnary which is used to add / update context extensions"""

        return {}

    def get_timestamp(self):
        """Returns the timestamp property for xapi_props"""

        return self.edx_event["time"]
