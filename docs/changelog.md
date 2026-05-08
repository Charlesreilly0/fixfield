---
layout: page
title: Changelog
permalink: /changelog/
---

## 0.2.0 — 2026-05-08

### Added
- **`ExternalField[T]`** — generic pass-through descriptor for non-decimal values inside a `Record` (UUIDs, strings, enums, plain ints, …).
  - `field_type` parameter with runtime type-checking on assignment.
  - `default_factory: Callable[[], T]` for per-instance mutable defaults (e.g. `uuid.uuid4`).
  - `json_encoder` / `json_decoder` wired through `to_json()` / `from_json()`.
  - Blocked inside `serializable=True` records.
  - Exported from the top-level `fixfield` package.
- **`FieldTemplate`** — reusable `Field` preset callable.
- Built-in field templates: `CurrencyField`, `PercentField`, `QuantityField`, `RateField`, `AccountNumberField`.
- `to_json()` / `from_json()` on `Record`.
- `signed` parameter on `Field` / `FieldTemplate` — rejects negative values.
- `serializable=True` class flag — validates all fields at class-definition time.

### Fixed
- `to_json()` raised `KeyError` when a nested `RecordField` contained fields not present in the outer record.
- `ExternalField.__get__` incorrectly treated an explicitly-set `None` as "not set", triggering `default_factory` again.

### Examples
- `examples/banking/` end-to-end demo updated to use `ExternalField` for `Transaction.tx_id` (UUID) and `memo` (str).

---

## 0.1.0 — 2026-05-07

Initial release.

- `FixedDecimal` scalar with per-instance precision, rounding, and overflow protection.
- `Field` descriptor with `places`, `rounding`, `default`, `digits`, `signed`.
- `Record` base class with auto-generated `__init__`, `__repr__`, `__eq__`.
- `RecordField[T]` for nested records.
- `to_string()` / `from_string()` for fixed-width flat-file serialisation.
- `RoundingStrategy` enum with 8 modes including `ROUND_HALF_ODD`.
- `FieldOverflowError` for integer-digit cap violations.
