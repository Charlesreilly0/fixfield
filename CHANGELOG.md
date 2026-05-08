# Changelog

All notable changes to `fixfield` will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.0] — 2026-05-08

### Added
- `FixedDecimal` — scalar fixed-decimal type with per-instance precision and rounding
- `RoundingStrategy` — enum of 8 rounding modes including `ROUND_HALF_ODD`
- `Field` — descriptor for declaring fixed-decimal fields on a `Record`
  - `places`, `digits`, `rounding`, `default` parameters
  - `width` property for fixed-width serialization
- `Record` — base class for structured groups of `Field` descriptors
  - Auto-generated `__init__`, `__repr__`, `__eq__`
  - `to_dict()`, `to_string()`, `from_string()`
- `RecordField[T]` — generic descriptor for embedding a nested `Record` as a field
  - `width` delegates to nested record's total width
  - Participates in `to_string()` / `from_string()` as a contiguous block
- `FieldOverflowError` — raised when a value exceeds declared integer-digit capacity
- `FieldValue` — public type alias for anything assignable to a `Field`
- Full arithmetic on `FixedDecimal`: `+`, `-`, `*`, `/`, unary `-`, `abs()`
- Reverse arithmetic operators: `__radd__`, `__rsub__`, `__rmul__`, `__rtruediv__`
- Full comparison protocol: `==`, `!=`, `<`, `<=`, `>`, `>=`
- `FixedDecimal.copy()` and `FixedDecimal.replace()` for non-destructive modification
- Fixed-width serialization: `Record.to_string()` / `Record.from_string()`
- `py.typed` marker for PEP 561 compliance
- Float input safety — floats converted via `str()` to avoid binary imprecision
