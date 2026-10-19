"""tidy-mcp: clean up messy folders with a local AI."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tidy-mcp")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0"
