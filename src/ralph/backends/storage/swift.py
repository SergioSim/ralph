"""Swift storage backend for Ralph"""

import inspect
import logging

from swiftclient.service import SwiftError, SwiftService

from ralph.defaults import (
    SWIFT_OS_AUTH_URL,
    SWIFT_OS_IDENTITY_API_VERSION,
    SWIFT_OS_PROJECT_DOMAIN_NAME,
    SWIFT_OS_USER_DOMAIN_NAME,
)
from ralph.exceptions import BackendParameterException

from ..mixins import HistoryMixin
from .base import BaseStorage

logger = logging.getLogger(__name__)


class SwiftStorage(HistoryMixin, BaseStorage):
    """OVH's Swift storage backend"""

    name = "swift"

    # pylint: disable=too-many-arguments

    def __init__(
        self,
        os_tenant_id,
        os_tenant_name,
        os_username,
        os_password,
        os_region_name,
        os_storage_url,
        os_user_domain_name=SWIFT_OS_USER_DOMAIN_NAME,
        os_project_domain_name=SWIFT_OS_PROJECT_DOMAIN_NAME,
        os_auth_url=SWIFT_OS_AUTH_URL,
        os_identity_api_version=SWIFT_OS_IDENTITY_API_VERSION,
    ):
        """Setup options for the SwiftService"""

        self.options = {
            "os_auth_url": os_auth_url,
            "os_identity_api_version": os_identity_api_version,
            "os_user_domain_name": os_user_domain_name,
            "os_project_domain_name": os_project_domain_name,
            "os_tenant_id": os_tenant_id,
            "os_tenant_name": os_tenant_name,
            "os_username": os_username,
            "os_password": os_password,
            "os_region_name": os_region_name,
            "os_storage_url": os_storage_url,
        }
        self._check_required_options()

    def _check_required_options(self):
        """Verify that all options are not None nor empty"""

        for option_name in self.options:
            option_value = self.options[option_name]
            # pylint: disable=protected-access
            if option_value is not None and not isinstance(
                option_value, inspect._empty
            ):
                continue
            raise BackendParameterException(
                f"SwiftStorage backend instance requires the `{option_name}` option to be set."
            )

    def list(self, details=False, new=False):
        """List files in the storage backend

        With details set to False we return only the names of the files.
        Example:
            2020-04-29.gz
            2020-04-30.gz
            2020-05-01.gz

        With details set to True we return JSON objects with more meta data.
        Example:
            {
                "bytes": 459,
                "last_modified": "2021-01-20T10:41:03.950030",
                "hash": "01018bc73b8b3491c6c3d543044a702b",
                "name": "2020-04-29.gz",
                "content_type": "application/gzip"
            }
        """
        try:
            with SwiftService(options=self.options) as swift:
                for page in swift.list():
                    if not page["success"]:
                        msg = "Failed to list container %s: %s"
                        logger.error(msg, page["container"], page["error"])
                        continue
                    archives = page["listing"]
                    if new:
                        archives = set(archives) - set(
                            entry.get("id")
                            for entry in filter(
                                lambda e: e["backend"] == self.name and e["command"] == "fetch",
                                self.history,
                            )
                    )
                    for archive in page["listing"]:
                        yield archive if details else archive["name"]
        except SwiftError as error:
            logger.error(error.value)
            raise error

    def url(self, name):
        """Get `name` file absolute URL"""

    def read(self, name, chunk_size=4096):
        """Read `name` file and stream its content by chunks of a given size"""
        logger.error("Read S")

    def write(self, name, chunk_size=4096, overwrite=False):
        """Write content to the `name` target"""
