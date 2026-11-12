from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("astra-spec")
except PackageNotFoundError:
    # package not installed
    __version__ = "0.0.0"
