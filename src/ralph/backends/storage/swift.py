"""Swift storage backend for Ralph"""

import datetime
import inspect
import logging
import sys

from swiftclient.exceptions import ClientException
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


def throws_swift_error(func):
    """Decorator catches SwiftError or ClientException, then logs and re-raises it"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (SwiftError, ClientException) as error:
            logger.error(error.value)
            raise error

    return wrapper


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

        self.container = os_storage_url.split("/")[-1]
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
            "os_storage_url": os_storage_url.replace(f"/{self.container}", ""),
        }
        self._check_options()

    def _check_options(self):
        """Verify that all options are not None nor empty"""

        for option_name in self.options:
            option = self.options[option_name]
            # pylint: disable=protected-access
            if option is not None and not isinstance(option, inspect._empty):
                continue
            raise BackendParameterException(
                f"SwiftStorage backend instance requires the `{option_name}` option to be set."
            )

    @throws_swift_error
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
                "hash": "b10a8db164e0754105b7a99be72e3fe5",
                "name": "2020-04-29.gz",
                "content_type": "application/gzip"
            }
        """

        archives_to_skip = set()
        if new:
            fetched_from_swift = (
                lambda e: e["backend"] == self.name and e["command"] == "fetch"
            )
            for entry in filter(fetched_from_swift, self.history):
                archives_to_skip.add(entry["id"])
        with SwiftService(options=self.options) as swift:
            for page in swift.list(container=self.container):
                if not page["success"]:
                    msg = "Failed to list container %s: %s"
                    logger.error(msg, page["container"], page["error"])
                    continue
                for archive in page["listing"]:
                    if (
                        new
                        and self._get_histrory_id(archive["name"]) in archives_to_skip
                    ):
                        continue
                    yield archive if details else archive["name"]

    def url(self, name):
        """Get `name` file absolute URL"""

        # What's the purpose of this function ? Seems not used anywhere.
        return f"{self.options.get('os_storage_url')}/{name}"

    def _get_histrory_id(self, name):
        return f"{self.container}/{name}"

    @throws_swift_error
    def read(self, name, chunk_size=None):
        """Read `name` file and stream its content by chunks of (max) 2 ** 16
        Not 100% sure why 2 ** 16 but may be because swift.service.py line 54 is:
            DISK_BUFFER = 2 ** 16 (TODO: Check this to be sure)
        """

        logger.debug("Getting archive: %s", name)

        with SwiftService(options=self.options) as swift:
            options = {"options": {"out_file": "-"}}
            download = next(
                swift.download(container=self.container, objects=[name], **options)
            )
            if "contents" not in download:
                raise BackendParameterException(
                    f"Failed to download {download['object']}, {download['error']}"
                )
            size = 0
            for chunk in download["contents"]:
                logger.debug("Chunk %s", len(chunk))
                size += len(chunk)
                sys.stdout.buffer.write(chunk)

            # Archive is supposed to have been fully fetched, add a new entry to
            # the history.
            self.append_to_history(
                {
                    "backend": self.name,
                    "command": "fetch",
                    "id": self._get_histrory_id(name),
                    "filename": name,
                    "size": size,
                    "fetched_at": datetime.datetime.now(
                        tz=datetime.timezone.utc
                    ).isoformat(),
                }
            )

    @throws_swift_error
    def write(self, name, chunk_size=4096, overwrite=False):
        """Write content to the `name` target"""
