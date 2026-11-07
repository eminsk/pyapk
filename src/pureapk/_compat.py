"""Compatibility layer across CPython (3.8 - 3.16), Free-Threaded No-GIL, and PyPy."""

from __future__ import annotations

import os
import sys
from typing import (
    Any,
    BinaryIO,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

# Detect runtime implementation
IS_PYPY: bool = sys.implementation.name == "pypy"
IS_FREE_THREADED: bool = getattr(sys, "_is_gil_enabled", lambda: True)() is False
PYTHON_VERSION: Tuple[int, ...] = sys.version_info[:3]

# Path-like type alias
PathOrBytes = Union[str, bytes, "os.PathLike[str]", "os.PathLike[bytes]", BinaryIO]

__all__ = [
    "IS_PYPY",
    "IS_FREE_THREADED",
    "PYTHON_VERSION",
    "PathOrBytes",
    "Any",
    "BinaryIO",
    "Callable",
    "Dict",
    "Iterable",
    "Iterator",
    "List",
    "Mapping",
    "NamedTuple",
    "Optional",
    "Sequence",
    "Set",
    "Tuple",
    "Union",
]
