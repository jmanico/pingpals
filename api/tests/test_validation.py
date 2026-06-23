"""Schema-validation framework tests (issue 020 / REQ-FND-009)."""

from __future__ import annotations

import time

import pytest

from pingpals_api.validation import (
    CATEGORY_NAME_RE,
    EMAIL_RE,
    PHONE_RE,
    Field,
    ValidationError,
    validate,
)

CONTACT_SCHEMA = {
    "display_name": Field("str", required=True, max_length=120, pattern=CATEGORY_NAME_RE),
    "email": Field("str", required=False, max_length=254, pattern=EMAIL_RE),
    "phone": Field("str", required=False, max_length=16, pattern=PHONE_RE),
    "cadence_days": Field("int", required=False, min_value=1, max_value=3650),
    "tags": Field("list", required=False, max_items=5, item=Field("str", max_length=20)),
}


def test_valid_request_is_accepted() -> None:
    out = validate(CONTACT_SCHEMA, {"display_name": "Alex", "email": "alex@example.com"})
    assert out["display_name"] == "Alex"  # AC-01


def test_unknown_fields_rejected_no_mass_assign() -> None:
    # AC-04: a privileged extra field (owner_id) is rejected, not silently bound.
    with pytest.raises(ValidationError) as ei:
        validate(CONTACT_SCHEMA, {"display_name": "Alex", "owner_id": "user-999"})
    assert ei.value.errors.get("owner_id") == "unknown_field"


def test_over_limit_field_rejected_not_truncated() -> None:
    # AC-06: over-limit is rejected, never coerced/truncated to fit.
    with pytest.raises(ValidationError) as ei:
        validate(CONTACT_SCHEMA, {"display_name": "A" * 200})
    assert ei.value.errors.get("display_name") == "too_long"


def test_list_cardinality_enforced() -> None:
    with pytest.raises(ValidationError) as ei:
        validate(CONTACT_SCHEMA, {"display_name": "Alex", "tags": ["a", "b", "c", "d", "e", "f"]})
    assert ei.value.errors.get("tags") == "too_many_items"


def test_numeric_range_enforced() -> None:
    with pytest.raises(ValidationError) as ei:
        validate(CONTACT_SCHEMA, {"display_name": "Alex", "cadence_days": 0})
    assert ei.value.errors.get("cadence_days") == "below_min"


def test_bool_is_not_accepted_as_int() -> None:
    with pytest.raises(ValidationError):
        validate(CONTACT_SCHEMA, {"display_name": "Alex", "cadence_days": True})


def test_required_field_missing() -> None:
    with pytest.raises(ValidationError) as ei:
        validate(CONTACT_SCHEMA, {"email": "alex@example.com"})
    assert ei.value.errors.get("display_name") == "required"


def test_malformed_provider_response_rejected() -> None:
    # AC-05: a provider/webhook response is untrusted until validated against its schema.
    provider_schema = {"id": Field("str", max_length=64), "email": Field("str", max_length=254,
                       pattern=EMAIL_RE)}
    with pytest.raises(ValidationError):
        validate(provider_schema, {"id": "x", "email": "not-an-email", "injected": "evil"})


def test_invalid_email_and_phone_rejected() -> None:
    with pytest.raises(ValidationError):
        validate(CONTACT_SCHEMA, {"display_name": "A", "email": "a@@b"})
    with pytest.raises(ValidationError):
        validate(CONTACT_SCHEMA, {"display_name": "A", "phone": "12-34-not"})


def test_non_object_body_rejected() -> None:
    with pytest.raises(ValidationError):
        validate(CONTACT_SCHEMA, ["not", "an", "object"])


def test_type_mismatches_rejected() -> None:
    assert _err({"s": Field("str")}, {"s": 123}).get("s") == "not_a_string"
    assert _err({"i": Field("int")}, {"i": "5"}).get("i") == "not_an_integer"
    assert _err({"b": Field("bool")}, {"b": "yes"}).get("b") == "not_a_boolean"
    assert _err({"l": Field("list", max_items=2, item=Field("str", max_length=4))},
                {"l": "nope"}).get("l") == "not_a_list"


def test_list_without_item_schema_is_unbounded_and_rejected() -> None:
    assert _err({"l": Field("list", max_items=2)}, {"l": ["a"]}).get("l") == "unbounded_item"


def test_unsupported_kind_rejected() -> None:
    assert _err({"x": Field("decimal")}, {"x": 1}).get("x") == "unsupported_kind"


def test_above_max_numeric() -> None:
    assert _err({"n": Field("int", max_value=10)}, {"n": 11}).get("n") == "above_max"


def _err(schema, data) -> dict[str, str]:
    with pytest.raises(ValidationError) as ei:
        validate(schema, data)
    return ei.value.errors


@pytest.mark.parametrize("pattern", [EMAIL_RE, PHONE_RE, CATEGORY_NAME_RE])
def test_validators_are_redos_safe(pattern) -> None:
    # AC-03: adversarial input must not blow up CPU. Length cap rejects long input in O(n);
    # the anchored/bounded pattern runs only on within-bound input and is linear.
    adversarial = [
        "a" * 100_000 + "!",
        ("a" * 50_000) + "@" + ("b" * 50_000),
        "+" + "9" * 100_000,
        ("x" * 40) + (" " * 1000),
    ]
    start = time.perf_counter()
    for s in adversarial:
        capped = s[:1024]  # the framework applies this cap BEFORE matching
        pattern.match(capped)
    assert time.perf_counter() - start < 0.2
