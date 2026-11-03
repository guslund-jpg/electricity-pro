"""Narrow untrusted JSON history values before model-specific validation."""

from collections.abc import Mapping
from decimal import Decimal


def stored_string(value: object) -> str:
    """Require a string without coercing malformed dates or enum values."""
    if not isinstance(value, str):
        raise ValueError("expected a stored string")
    return value


def stored_decimal(value: object) -> Decimal:
    """Preserve Decimal conversion of stored strings and numeric scalars.

    Finiteness, sign and range remain the owning model's responsibility.
    Decimal instances are also accepted for in-memory round trips.
    """
    if not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("expected a stored decimal")
    return Decimal(value)


def stored_list(value: object) -> list[object]:
    """Require a JSON array, including an empty history array."""
    if not isinstance(value, list):
        raise ValueError("expected a stored list")
    return value


def stored_record(value: object) -> Mapping[str, object]:
    """Require a record with string keys; retain unknown fields for readers."""
    if not isinstance(value, Mapping):
        raise ValueError("expected a stored record")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError("expected a stored string key")
        result[key] = item
    return result
