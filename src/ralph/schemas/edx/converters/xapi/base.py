"""Base Xapi Converter"""

from ralph.schemas.edx.converters.base_converter import BaseConverter


class BaseXapiConverter(BaseConverter):
    """Base xAPI Converter"""

    _platform = ""
    _anonymize = False
    _anonymization_hash_slice_indexes = []
