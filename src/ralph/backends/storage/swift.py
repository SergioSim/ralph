"""Swift storage backend for Ralph"""

import inspect
import logging
import sys

from swiftclient.exceptions import ClientException
from swiftclient.service import SwiftError, SwiftService, SwiftUploadObject

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
        self._check_options()
        self.container = os_storage_url.split("/")[-1]
        self.options["os_storage_url"] = os_storage_url.replace(
            f"/{self.container}", ""
        )

    def _check_options(self):
        """Verify that all options are not None nor empty"""

        for option_name in self.options:
            option = self.options[option_name]
            # pylint: disable=protected-access
            if option is not None and not isinstance(option, inspect._empty):
                continue
            msg = "SwiftStorage backend instance requires the %s option to be set"
            logger.error(msg, option_name)
            raise BackendParameterException(msg % option_name)

    @throws_swift_error
    def list(self, details=False, new=False):
        """List files in the storage backend"""

        archives_to_skip = set()
        if new:
            for entry in filter(self.fetched_from_backend, self.history):
                archives_to_skip.add(entry["id"])
        with SwiftService(self.options) as swift:
            for page in swift.list(self.container):
                if not page["success"]:
                    msg = "Failed to list container %s: %s"
                    logger.error(msg, page["container"], page["error"])
                    continue
                for archive in page["listing"]:
                    if new and archive["name"] in archives_to_skip:
                        continue
                    yield archive if details else archive["name"]

    def url(self, name):
        """Get `name` file absolute URL"""

        # What's the purpose of this function ? Seems not used anywhere.
        return f"{self.options.get('os_storage_url')}/{name}"

    @throws_swift_error
    def read(self, name, chunk_size=None):
        """Read `name` object and stream its content in chunks of (max) 2 ** 16

        Why chunks of (max) 2 ** 16 ?
            Because SwiftService opens a file to stream the object into:
            See swiftclient.service.py:2082 open(filename, 'rb', DISK_BUFFER)
            Where filename = "/dev/stdout" and DISK_BUFFER = 2 ** 16
        """

        logger.debug("Getting archive: %s", name)

        options = {"options": {"out_file": "/dev/stdout"}}
        with SwiftService(self.options) as swift:
            download = next(swift.download(self.container, [name], **options))
        if not download["success"]:
            logger.error(download["error"])
            return

        # Archive fetched, add a new entry to the history
        self.append_to_history(
            {
                "backend": self.name,
                "command": "fetch",
                "id": name,
                "size": download["read_length"],
                "fetched_at": self.get_current_iso_time(),
            }
        )

    @throws_swift_error
    def write(self, name, chunk_size=None, overwrite=False):
        """Write content to the `name` target in chunks of (max) 2 ** 16"""

        if not overwrite and name in list(self.list()):
            msg = "%s already exists and overwrite is not allowed"
            logger.error(msg, name)
            raise FileExistsError(msg % name)

        logger.debug("Creating archive: %s", name)

        swift_object = SwiftUploadObject(sys.stdin.buffer, object_name=name)
        with SwiftService(self.options) as swift:
            for upload in swift.upload(self.container, [swift_object]):
                if not upload["success"]:
                    logger.error(upload["error"])
                    raise BackendParameterException(upload["error"])

        # Archive written, add a new entry to the history
        self.append_to_history(
            {
                "backend": self.name,
                "command": "push",
                "id": name,
                "pushed_at": self.get_current_iso_time(),
            }
        )
