"""Whether one path on this machine lies inside another."""

from __future__ import annotations

import os


def _normalized(path: str) -> str:
    full = os.path.abspath(os.path.expanduser(path))
    drive, rest = os.path.splitdrive(full)
    if drive and not rest:
        # A bare share, \\server\share, has a drive and no root, which
        # commonpath reads as a relative path and refuses to compare.
        full = drive + os.sep
    return os.path.normcase(full)


def is_within(path: str, root: str) -> bool:
    """True when ``path`` is ``root`` or anything under it.

    Case and separators follow this OS, and ``//server/share`` -- how Qt's
    file dialogs spell a network path -- matches ``\\\\server\\share``. A
    mirror set to the root of a network share used to contain nothing at all:
    the bare share has no root part, and ``commonpath`` raised on it.
    """
    if not path or not root:
        return False
    try:
        base = _normalized(root)
        common = os.path.commonpath([base, _normalized(path)])
    except (OSError, ValueError):
        # Different drives on Windows, or a path that cannot be resolved.
        return False
    return os.path.normcase(common).rstrip("\\/") == base.rstrip("\\/")
