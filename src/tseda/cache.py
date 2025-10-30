"""This module provides a caching mechanism for the TSeDA application,
utilizing the `diskcache` library."""

import pathlib

import appdirs
import diskcache


def get_cache_dir() -> pathlib.Path:
    """Retrieves the user's cache directory for the TSeDA application. Creates
    the directory if it doesn't exist, ensuring its creation along with any
    necessary parent directories.

    Returns:
        pathlib.Path: The path to the cache directory.
    """
    cache_dir = pathlib.Path(appdirs.user_cache_dir("tseda", "tseda"))
    cache_dir.mkdir(exist_ok=True, parents=True)
    return cache_dir


cache = diskcache.Cache(get_cache_dir())
