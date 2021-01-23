"""Base storage backend for Ralph"""

from abc import ABC, abstractmethod


class BaseStorage(ABC):
    """Base storage backend interface"""

    name = "base"

    @abstractmethod
    def list(self, details=False, new=False):
        """List files in the storage backend"""

    @abstractmethod
    def url(self, name):
        """Get `name` file absolute URL"""

    @abstractmethod
    def read(self, name, chunk_size=4096):
        """Read `name` file and stream its content by chunks of a given size"""

    @abstractmethod
    def write(self, name, chunk_size=4096, overwrite=False):
        """Write content to the `name` target"""

    def fetched_from_backend(self, entry):
        """Return if the entry was fetched by the backend"""
        return entry["backend"] == self.name and entry["command"] == "fetch"
