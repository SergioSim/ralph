"""Tests for Ralph swift storage backend"""

import datetime
import hashlib
import inspect
import json
from unittest import TestCase

import pytest
import requests
from click.testing import CliRunner

from ralph.backends.storage.swift import (
    SwiftError,
    SwiftService,
    SwiftStorage,
    throws_swift_error,
)
from ralph.cli import cli
from ralph.defaults import HISTORY_FILE
from ralph.exceptions import BackendParameterException

AUTH_TOKEN_HEADER = {"X-Auth-Token": None}
FREEZED_NOW = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
SWIFT_OBJECT = "new_object"
SWIFT_OPTIONS = {
    "os_tenant_id": None,
    "os_tenant_name": "RegionOne",
    "os_username": "demo",
    "os_password": "demo",
    "os_region_name": "RegionOne",
    "os_storage_url": None,
    "os_user_domain_name": "Default",
    "os_project_domain_name": "Default",
    "os_auth_url": "http://swift:35357/v3/",
    "os_identity_api_version": "3",
}
HISTORY = [
    {
        "backend": "swift",
        "command": "fetch",
        "id": "2020-04-29.gz",
        "filename": "2020-04-29.gz",
        "size": 23424233,
        "fetched_at": "2020-10-07T16:40:25.887664+00:00",
    },
    {
        "backend": "swift",
        "command": "fetch",
        "id": "2020-04-30.gz",
        "filename": "2020-04-30.gz",
        "size": 23424233,
        "fetched_at": "2020-10-07T16:37:25.887664+00:00",
    },
]
LISTING = [
    {
        "bytes": 23424233,
        "last_modified": "2021-01-20T10:41:03.950030",
        "hash": "01018bc73b8b3491c6c3d543044a702b",
        "name": "2020-04-29.gz",
        "content_type": "application/gzip",
    },
    {
        "bytes": 23424233,
        "last_modified": "2021-01-22T13:53:58.751680",
        "hash": "b9f999739e55ab42ad852453d145a6a9",
        "name": "2020-04-30.gz",
        "content_type": "text/plain",
    },
    {
        "bytes": 23424233,
        "last_modified": "2021-01-22T13:53:03.541030",
        "hash": "b9f999739e55ab42ad852453d145a6a9",
        "name": "2020-05-01.gz",
        "content_type": "text/plain",
    },
]


def setup_module(module):  # pylint:disable=unused-argument
    """Connect to Swift and create a container"""

    keystone_v3_auth_url = SWIFT_OPTIONS["os_auth_url"] + "auth/tokens"
    valid_v3_auth_data = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "name": SWIFT_OPTIONS["os_username"],
                        "domain": {"name": SWIFT_OPTIONS["os_user_domain_name"]},
                        "password": SWIFT_OPTIONS["os_password"],
                    }
                },
            },
            "scope": {
                "project": {
                    "domain": {"id": "default"},
                    "name": "test",
                }
            },
        }
    }
    headers = {"Content-Type": "application/json"}
    # Authenticate with keystone
    try:
        auth_response = requests.post(
            keystone_v3_auth_url, json=valid_v3_auth_data, headers=headers
        )
    except requests.exceptions.RequestException:
        SWIFT_OPTIONS["os_auth_url"] = "http://localhost:35357/v3/"
        keystone_v3_auth_url = SWIFT_OPTIONS["os_auth_url"] + "auth/tokens"
        auth_response = requests.post(
            keystone_v3_auth_url, json=valid_v3_auth_data, headers=headers
        )
    assert auth_response.status_code == 201
    AUTH_TOKEN_HEADER["X-Auth-Token"] = auth_response.headers["X-Subject-Token"]
    auth_tenant_url = auth_response.json()["token"]["catalog"][-1]["endpoints"][-1][
        "url"
    ]
    auth_tenant = auth_tenant_url.split("/")[-1]
    SWIFT_OPTIONS["os_tenant_id"] = auth_tenant[4:]
    SWIFT_OPTIONS[
        "os_storage_url"
    ] = f"http://swift:8080/v1/{auth_tenant}/demo_container"
    # Create container in SWIFT
    try:
        swift_response = requests.put(
            SWIFT_OPTIONS["os_storage_url"], headers=AUTH_TOKEN_HEADER
        )
    except requests.exceptions.RequestException:
        SWIFT_OPTIONS[
            "os_storage_url"
        ] = f"http://localhost:8080/v1/{auth_tenant}/demo_container"
        swift_response = requests.put(
            SWIFT_OPTIONS["os_storage_url"], headers=AUTH_TOKEN_HEADER
        )
    assert swift_response.status_code in (201, 202)


def teardown_module(module):  # pylint:disable=unused-argument
    """Delete the container and all objects"""

    swift_delete_object = requests.delete(
        f"{SWIFT_OPTIONS['os_storage_url']}/{SWIFT_OBJECT}", headers=AUTH_TOKEN_HEADER
    )
    assert swift_delete_object.status_code == 204
    swift_delete = requests.delete(
        SWIFT_OPTIONS["os_storage_url"], headers=AUTH_TOKEN_HEADER
    )
    assert swift_delete.status_code == 204


def setup_swift_environment(monkeypatch):
    """Setup the swift environment for the cli"""

    monkeypatch.setenv("RALPH_SWIFT_OS_USERNAME", SWIFT_OPTIONS["os_username"])
    monkeypatch.setenv("RALPH_SWIFT_OS_PASSWORD", SWIFT_OPTIONS["os_password"])
    monkeypatch.setenv(
        "RALPH_SWIFT_OS_USER_DOMAIN_NAME", SWIFT_OPTIONS["os_user_domain_name"]
    )
    monkeypatch.setenv(
        "RALPH_SWIFT_OS_PROJECT_DOMAIN_NAME", SWIFT_OPTIONS["os_project_domain_name"]
    )
    monkeypatch.setenv("RALPH_SWIFT_OS_AUTH_URL", SWIFT_OPTIONS["os_auth_url"])
    monkeypatch.setenv(
        "RALPH_SWIFT_OS_IDENTITY_API_VERSION", SWIFT_OPTIONS["os_identity_api_version"]
    )
    monkeypatch.setenv("RALPH_SWIFT_OS_REGION_NAME", SWIFT_OPTIONS["os_region_name"])
    monkeypatch.setenv("RALPH_SWIFT_OS_TENANT_ID", SWIFT_OPTIONS["os_tenant_id"])
    monkeypatch.setenv("RALPH_SWIFT_OS_TENANT_NAME", SWIFT_OPTIONS["os_tenant_name"])
    monkeypatch.setenv("RALPH_SWIFT_OS_STORAGE_URL", SWIFT_OPTIONS["os_storage_url"])


def list_page(success=True):
    """Mocks the output of SwiftService.list"""
    page = {"success": success, "container": "ralph_logs_container"}
    listing = {"listing": LISTING}
    error = {"error": "Container not found"}
    page.update(listing if success else error)
    return page


@pytest.mark.parametrize("option", SWIFT_OPTIONS)
@pytest.mark.parametrize(
    "value", [None, inspect._empty()]  # pylint: disable=protected-access
)
def test_given_none_or_empty_option_swift_storage_should_raise_exception(
    option, value, swift
):
    """Check that SwiftStorage raises BackendParameterException for None or empty options"""

    options = swift.options
    options[option] = value
    msg = f"SwiftStorage backend instance requires the {option} option to be set"
    with pytest.raises(BackendParameterException, match=msg):
        SwiftStorage(**options)


@pytest.mark.parametrize("exception", [SwiftError, SwiftError])
def test_throws_swift_error_decorator_should_re_raise_exception(exception):
    """Check that when a function is decorated with swift_error_decorator
    it catches, logs and re-raises SwiftError or ClientException
    """

    msg = f"Error: {exception.__class__}"

    @throws_swift_error
    def will_throw_exception():
        """Throws an instance of exception"""
        raise exception(msg)

    with TestCase().assertLogs("ralph", level="ERROR") as cm:
        with pytest.raises(exception, match=msg):
            will_throw_exception()

        assert cm.output == [f"ERROR:ralph.backends.storage.swift:{msg}"]


@pytest.mark.parametrize("count", [1, 2])
def test_given_a_successful_connection_list_should_yield_archive_names(
    count, swift, monkeypatch, fs
):  # pylint:disable=invalid-name
    """Given SwiftService.list method successfully connects to the Swift storage
    The SwiftStorage list method should yield the archives
    """

    def mock_list_with_pages(*args, **kwargs):  # pylint:disable=unused-argument
        return [list_page(success=True)] * count

    monkeypatch.setattr(SwiftService, "list", mock_list_with_pages)
    fs.create_file(HISTORY_FILE, contents=json.dumps(HISTORY))

    names = ["2020-04-29.gz", "2020-04-30.gz", "2020-05-01.gz"]
    assert list(swift.list()) == names * count
    assert list(swift.list(new=True)) == ["2020-05-01.gz"] * count
    assert list(swift.list(details=True)) == LISTING * count


@pytest.mark.parametrize("count", [1, 2])
def test_given_an_unsuccessful_connection_list_should_log_the_error(
    count, swift, monkeypatch, fs
):  # pylint:disable=invalid-name
    """Given SwiftService.list method fails to retrieve the list of archives
    The SwiftStorage list method should log the error and not yield anything
    """

    def mock_list_with_pages(*args, **kwargs):  # pylint:disable=unused-argument
        return [list_page(success=False)] * count

    monkeypatch.setattr(SwiftService, "list", mock_list_with_pages)
    fs.create_file(HISTORY_FILE, contents=json.dumps(HISTORY))

    with TestCase().assertLogs("ralph", level="ERROR") as cm:
        assert list(swift.list()) == []
        assert list(swift.list(new=True)) == []
        assert list(swift.list(details=True)) == []
        msg = "Failed to list container ralph_logs_container: Container not found"
        assert cm.output == [f"ERROR:ralph.backends.storage.swift:{msg}"] * 3 * count


def test_given_a_successful_connection_and_a_valid_name_read_should_write_to_history(
    swift, monkeypatch, fs
):  # pylint:disable=invalid-name
    """Given SwiftService.download method successfully retrieves from the Swift storage the object
    with the provided name (the object exists)
    The SwiftStorage read method should write the entry to the history
    """

    def mock_successful_download(*args, **kwargs):  # pylint:disable=unused-argument
        yield {"success": True, "read_length": 23424233}

    monkeypatch.setattr(SwiftService, "download", mock_successful_download)
    monkeypatch.setattr(SwiftStorage, "get_current_iso_time", lambda x: FREEZED_NOW)
    fs.create_file(HISTORY_FILE, contents=json.dumps(HISTORY))

    swift.read("2020-04-29.gz")
    assert swift.history == HISTORY + [
        {
            "backend": "swift",
            "command": "fetch",
            "id": "2020-04-29.gz",
            "size": 23424233,
            "fetched_at": FREEZED_NOW,
        }
    ]


def test_given_an_invalid_name_read_should_log_the_error_and_not_write_to_history(
    swift, monkeypatch, fs
):  # pylint:disable=invalid-name
    """Given SwiftService.download method fails to retrieve from the Swift storage the object
    with the provided name (the object does not exists on Swift)
    The SwiftStorage read method should log the error and not write to history
    """

    error = 'ClientException("Object GET failed")'

    def mock_failed_download(*args, **kwargs):  # pylint:disable=unused-argument
        yield {"success": False, "error": error}

    monkeypatch.setattr(SwiftService, "download", mock_failed_download)
    fs.create_file(HISTORY_FILE, contents=json.dumps(HISTORY))

    with TestCase().assertLogs("ralph", level="ERROR") as cm:
        swift.read("2020-04-31.gz")
        assert cm.output == [f"ERROR:ralph.backends.storage.swift:{error}"]
        assert swift.history == HISTORY


@pytest.mark.parametrize("overwrite", [False, True])
@pytest.mark.parametrize("new_archive", [False, True])
def test_given_a_successful_connection_write_should_write_to_history_new_or_overwriten_archives(
    overwrite, new_archive, swift, monkeypatch, fs
):  # pylint:disable=invalid-name
    """Given SwiftService.(list/upload) method successfully connects to the Swift storage
    The SwiftStorage write method should update the history file when overwrite is True
    or when the name of the archive is not in the history.
    In case overwrite is False and the archive is in the history, the write method should
    raise a FileExistsError
    """

    def mock_successful_upload(*args, **kwargs):  # pylint:disable=unused-argument
        yield {"success": True}

    def mock_successful_list(*args, **kwargs):  # pylint:disable=unused-argument
        return [list_page(success=True)]

    monkeypatch.setattr(SwiftService, "upload", mock_successful_upload)
    monkeypatch.setattr(SwiftService, "list", mock_successful_list)
    monkeypatch.setattr(SwiftStorage, "get_current_iso_time", lambda x: FREEZED_NOW)
    fs.create_file(HISTORY_FILE, contents=json.dumps(HISTORY))

    archive_name = "not_in_history.gz" if new_archive else "2020-04-29.gz"
    new_history_entry = [
        {
            "backend": "swift",
            "command": "push",
            "id": archive_name,
            "pushed_at": FREEZED_NOW,
        }
    ]

    if not overwrite and not new_archive:
        new_history_entry = []
        msg = f"{archive_name} already exists and overwrite is not allowed"
        with TestCase().assertLogs("ralph", level="ERROR") as cm:
            with pytest.raises(FileExistsError, match=msg):
                swift.write(archive_name, overwrite=overwrite)
            assert cm.output == [f"ERROR:ralph.backends.storage.swift:{msg}"]
    else:
        swift.write(archive_name, overwrite=overwrite)
    assert swift.history == HISTORY + new_history_entry


def test_given_an_unsuccessful_connection_write_should_log_the_error(
    swift, monkeypatch, fs
):  # pylint:disable=invalid-name
    """Given SwiftService.upload method fails to write the archive
    The SwiftStorage write method should log the error, raise a BackendParameterException
    and not write to history
    """

    error = "Unauthorized. Check username/id, password"

    def mock_failed_upload(*args, **kwargs):  # pylint:disable=unused-argument
        yield {"success": False, "error": error}

    def mock_successful_list(*args, **kwargs):  # pylint:disable=unused-argument
        return [list_page(success=True)]

    monkeypatch.setattr(SwiftService, "upload", mock_failed_upload)
    monkeypatch.setattr(SwiftService, "list", mock_successful_list)
    fs.create_file(HISTORY_FILE, contents=json.dumps(HISTORY))

    with TestCase().assertLogs("ralph", level="ERROR") as cm:
        with pytest.raises(BackendParameterException, match=error):
            swift.write("2020-04-29.gz", overwrite=True)
        assert cm.output == [f"ERROR:ralph.backends.storage.swift:{error}"]
        assert swift.history == HISTORY


def test_url_should_concatenate_the_storage_url_and_name(swift):
    """Check the url method returns `os_storage_url/name`"""

    assert swift.url("name") == "os_storage_url/name"


def test_command_usage(monkeypatch, fs):  # pylint: disable=invalid-name
    """Test a common command usage scenario (list/push/fetch) with swift backend"""

    setup_swift_environment(monkeypatch)
    fs.create_file(HISTORY_FILE, contents=json.dumps([]))
    fs.create_file("/dev/stdout")
    runner = CliRunner()

    # When we list an empty container, there is no output
    result = runner.invoke(cli, ["-v", "ERROR", "list", "-b", "swift"])
    assert result.exit_code == 0
    assert result.output == ""

    # When we fetch an non existing object, we get an error message
    result = runner.invoke(
        cli, ["-v", "ERROR", "fetch", "-b", "swift", "not_existing_object"]
    )
    assert result.exit_code == 0
    assert "not_existing_object 404 Not Found" in result.output

    # When we push a new object, it appears in the next list command
    # And we can retrieve it with the fetch command
    result = runner.invoke(
        cli, ["-v", "ERROR", "push", "-b", "swift", SWIFT_OBJECT], input="some content"
    )
    assert result.exit_code == 0
    assert result.output == ""

    # We should see the new_object in the list
    result = runner.invoke(cli, ["-v", "ERROR", "list", "-b", "swift"])
    assert result.exit_code == 0
    assert result.output == SWIFT_OBJECT + "\n"
    # Same output with the new option (we haven't fetched the object before)
    result = runner.invoke(cli, ["-v", "ERROR", "list", "-b", "swift", "-n"])
    assert result.exit_code == 0
    assert result.output == SWIFT_OBJECT + "\n"
    # With the details option we should see more details
    result = runner.invoke(cli, ["-v", "ERROR", "list", "-b", "swift", "--details"])
    assert result.exit_code == 0
    json_output = json.loads(result.output)
    assert json_output["bytes"] == 12
    assert json_output["name"] == SWIFT_OBJECT
    assert json_output["content_type"] == "application/octet-stream"
    assert json_output["hash"] == hashlib.md5(b"some content").hexdigest()
    assert "last_modified" in json_output
    # We should get the objects content with fetch
    result = runner.invoke(cli, ["-v", "ERROR", "fetch", "-b", "swift", SWIFT_OBJECT])
    assert result.exit_code == 0
    # It's not in result.output this time as we write directly to /dev/stdout
    with open("/dev/stdout", "r") as file:
        assert file.read() == "some content"
    # And now if we retrieve the list of new objects the list should be empty
    # Because we already had fetched the object before
    result = runner.invoke(cli, ["-v", "ERROR", "list", "-b", "swift", "-n"])
    assert result.exit_code == 0
    assert result.output == ""

    # When we try to overwrite an existing object without setting the -f option
    # we get an error
    result = runner.invoke(
        cli,
        ["-v", "ERROR", "push", "-b", "swift", SWIFT_OBJECT],
        input="overwritten content",
    )
    assert result.exit_code == 1
    assert (
        f"{SWIFT_OBJECT} already exists and overwrite is not allowed" in result.output
    )
    # We should get it's original content with fetch
    result = runner.invoke(cli, ["-v", "ERROR", "fetch", "-b", "swift", SWIFT_OBJECT])
    assert result.exit_code == 0
    with open("/dev/stdout", "r") as file:
        assert file.read() == "some content"

    # When we try to overwrite an existing object and set the -f option
    # we should succeed
    result = runner.invoke(
        cli,
        ["-v", "ERROR", "push", "-b", "swift", "-f", SWIFT_OBJECT],
        input="overwritten content",
    )
    # We should get it's overwritten content with fetch
    result = runner.invoke(cli, ["-v", "ERROR", "fetch", "-b", "swift", SWIFT_OBJECT])
    assert result.exit_code == 0
    with open("/dev/stdout", "r") as file:
        assert file.read() == "overwritten content"
