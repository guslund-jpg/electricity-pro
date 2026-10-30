"""Resolve saved entry settings without Home Assistant or value normalization."""

from collections.abc import Mapping
from typing import Any


def resolve_settings(
    data: Mapping[str, Any], options: Mapping[str, Any]
) -> dict[str, Any]:
    """Return a fresh shallow overlay with options taking precedence.

    Presence, not truthiness, determines precedence: explicit None, zero, False,
    empty strings and empty collections override data. Missing keys remain
    missing. Callers retain their own defaults, validation and normalization.
    Neither input mapping is modified; nested values are not copied or merged.
    Resolve again when fresh options are needed rather than caching this result.
    """
    return {**data, **options}
