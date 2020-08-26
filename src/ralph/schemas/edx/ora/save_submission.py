"""
openassessmentblock.save_submission event schema definition
"""
import json

from marshmallow import Schema, ValidationError, fields, validates, validates_schema
from marshmallow.validate import Equal, Length

from ..base import BaseEventSchema, ContextSchema


class SaveSubmissionEventSchema(Schema):
    """Represents the event field of an
    openassessmentblock.save_submission
    """

    saved_response = fields.Str(required=True)

    # pylint: disable=no-self-use, unused-argument

    @validates("saved_response")
    def validate_saved_response(self, value):
        """"check saved_response field is a JSON string containing the key `parts`
        and that the value is a list"""
        try:
            saved_response = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            raise ValidationError("saved_response should be a parsable JSON string")
        if "parts" not in saved_response:
            raise ValidationError("saved_response should contain the key `parts`")
        if not isinstance(saved_response["parts"], list):
            raise ValidationError("saved_response.parts should be an array")


class SaveSubmissionSchema(BaseEventSchema):
    """Represents the openassessmentblock.save_submission event
    This type of event is triggered after the user clicks on the
    `Save you progress` button to save the current state of a
    open assessment block
    """

    # pylint: disable=no-self-use
    @validates_schema
    def validate_context_path(self, data, **kwargs):
        """the event.context.path should end with:
        "save_submission"
        """
        valid_path = "/handler/save_submission"
        path = data["context"]["path"]
        path_len = len(valid_path)
        if path[-path_len:] != valid_path:
            raise ValidationError(
                f"context.path should end with: "
                f"{valid_path} "
                f"but {path[-path_len:]} does not match!"
            )

    username = fields.Str(required=True, validate=Length(min=2, max=30))
    event_type = fields.Str(
        required=True,
        validate=Equal(
            comparable="openassessmentblock.save_submission",
            error="The event event_type field is not `openassessmentblock.save_submission`",
        ),
    )
    event = fields.Nested(SaveSubmissionEventSchema(), required=True)
    context = fields.Nested(ContextSchema(), required=True)
    page = fields.Str(
        required=True,
        validate=Equal(
            comparable="x_module", error='The event page field is not "x_module"'
        ),
    )
