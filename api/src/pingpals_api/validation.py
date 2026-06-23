"""Schema-validation framework — reject over sanitize, bounded, ReDoS-safe (issue 020).

The single backend chokepoint behind FR-1.4 / SEC-4.1. Every inbound edge (user input, provider
responses, webhook payloads) is validated against an explicit schema and REJECTED on failure —
never coerced, truncated, or mass-assigned. All fields declare explicit upper bounds. Patterns are
anchored/bounded and the length cap is applied BEFORE any regex, so adversarial input is rejected
in linear time (no catastrophic backtracking). Untrusted input is never compiled into a regex.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# --- Precompiled, anchored, bounded validators (ReDoS-safe). Length is capped before matching. ---
# Deliberately simple character classes with bounded quantifiers — no nested/ambiguous quantifiers.
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s.]{1,63}(?:\.[^@\s.]{1,63}){1,8}$")
PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")  # E.164-style digits, optional leading '+'
CATEGORY_NAME_RE = re.compile(r"^[\w .,'\-]{1,60}$")  # letters/space/basic punctuation

MAX_STRING = 1024  # absolute hard cap any string field is checked against first


class ValidationError(Exception):
    """Field-level validation failure. ``errors`` maps field name -> stable error code."""

    def __init__(self, errors: dict[str, str]) -> None:
        super().__init__("validation_failed")
        self.errors = errors


class _FieldError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


@dataclass(frozen=True)
class Field:
    """Declarative field bound. Every field declares explicit limits (no open-ended fields)."""

    kind: str  # "str" | "int" | "bool" | "list"
    required: bool = True
    max_length: int | None = None  # str: max chars (<= MAX_STRING)
    pattern: re.Pattern[str] | None = None  # str: anchored, bounded
    min_value: int | None = None  # int range
    max_value: int | None = None
    max_items: int | None = None  # list cardinality
    item: Field | None = None  # list element schema


def validate(schema: dict[str, Field], data: Any) -> dict[str, Any]:
    """Validate ``data`` against ``schema``. Reject unknown fields; never mass-assign or coerce."""
    if not isinstance(data, dict):
        raise ValidationError({"_body": "object_required"})

    errors: dict[str, str] = {}
    # Unknown/extra fields (incl. privileged ones like owner_id/consent) are rejected, not ignored.
    for unknown in set(data) - set(schema):
        errors[unknown] = "unknown_field"

    result: dict[str, Any] = {}
    for name, field in schema.items():
        if name not in data:
            if field.required:
                errors[name] = "required"
            continue
        try:
            result[name] = _validate_field(field, data[name])
        except _FieldError as exc:
            errors[name] = exc.code

    if errors:
        raise ValidationError(errors)
    return result


def _validate_field(field: Field, value: Any) -> Any:
    if field.kind == "str":
        return _validate_str(field, value)
    if field.kind == "int":
        return _validate_int(field, value)
    if field.kind == "bool":
        if not isinstance(value, bool):
            raise _FieldError("not_a_boolean")
        return value
    if field.kind == "list":
        return _validate_list(field, value)
    raise _FieldError("unsupported_kind")


def _validate_str(field: Field, value: Any) -> str:
    if not isinstance(value, str):
        raise _FieldError("not_a_string")
    cap = min(field.max_length or MAX_STRING, MAX_STRING)
    # Length cap BEFORE any regex — adversarial long input is rejected in O(n), never truncated.
    if len(value) > cap:
        raise _FieldError("too_long")
    if field.pattern is not None and field.pattern.match(value) is None:
        raise _FieldError("invalid_format")
    return value


def _validate_int(field: Field, value: Any) -> int:
    # bool is a subclass of int — reject it explicitly so True/False can't masquerade as 1/0.
    if isinstance(value, bool) or not isinstance(value, int):
        raise _FieldError("not_an_integer")
    if field.min_value is not None and value < field.min_value:
        raise _FieldError("below_min")
    if field.max_value is not None and value > field.max_value:
        raise _FieldError("above_max")
    return value


def _validate_list(field: Field, value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise _FieldError("not_a_list")
    cap = field.max_items if field.max_items is not None else 0
    if len(value) > cap:
        raise _FieldError("too_many_items")
    if field.item is None:
        raise _FieldError("unbounded_item")  # a list field MUST declare its element schema
    return [_validate_field(field.item, v) for v in value]
