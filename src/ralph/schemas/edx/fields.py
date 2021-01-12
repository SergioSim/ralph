"""Schema field definitions"""

from ipaddress import IPv4Address

from marshmallow import ValidationError
from marshmallow.fields import Field

class IPv4AddressField(Field):
    """IPv4 Address that serializes to a string of numbers and deserializes
    to a IPv4Address object.
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if not value:
            return ""
        return value.exploded

    def _deserialize(self, value, attr, data, **kwargs):
        if not value:
            return ""
        try:
            return IPv4Address(value)
        except ValueError as error:
            raise ValidationError("Invalid IPv4 Address") from error
