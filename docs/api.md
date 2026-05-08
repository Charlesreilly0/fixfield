---
layout: page
title: API Reference
permalink: /api/
---

## `fixfield` — public API

```python
from fixfield import (
    # Core scalar
    FixedDecimal,
    FieldOverflowError,
    RoundingStrategy,

    # Field descriptors
    Field,
    FieldValue,       # type alias: int | float | str | Decimal | FixedDecimal
    FieldTemplate,
    ExternalField,

    # Built-in field templates
    CurrencyField,
    PercentField,
    QuantityField,
    RateField,
    AccountNumberField,

    # Record
    Record,
    RecordField,
)
```

---

## `FixedDecimal`

```python
FixedDecimal(
    value: int | float | str | Decimal | FixedDecimal,
    places: int = 2,
    rounding: RoundingStrategy = RoundingStrategy.ROUND_HALF_UP,
    digits: int | None = None,
)
```

Scalar fixed-decimal value. Arithmetic always rounds the result to the **left operand's** precision.

### Attributes

| Name | Type | Description |
|---|---|---|
| `places` | `int` | Number of decimal places |
| `rounding` | `RoundingStrategy` | Rounding strategy |
| `digits` | `int \| None` | Max integer digits |

### Methods / operators

| Name | Description |
|---|---|
| `+`, `-`, `*`, `/` | Arithmetic; result precision comes from left operand |
| `-x`, `abs(x)` | Unary negation, absolute value |
| `==`, `<`, `<=`, `>`, `>=` | Comparisons (precision-aware equality) |
| `str(x)` | Canonical decimal string |
| `repr(x)` | Debug representation |
| `hash(x)` | Stable hash (precision-aware) |
| `.copy()` | Return an identical copy |
| `.replace(places=…, rounding=…, digits=…)` | Return a copy with overrides |

---

## `Field`

```python
Field(
    places: int = 2,
    rounding: RoundingStrategy = RoundingStrategy.ROUND_HALF_UP,
    default: FieldValue | None = None,
    digits: int | None = None,
    signed: bool = True,
)
```

Descriptor for use inside a `Record`. Enforces precision on every `__set__`.

---

## `FieldTemplate`

```python
FieldTemplate(
    places: int = 2,
    rounding: RoundingStrategy = RoundingStrategy.ROUND_HALF_UP,
    default: FieldValue | None = None,
    digits: int | None = None,
    signed: bool = True,
)
```

A reusable `Field` factory. Call it like `Field` to produce a `Field` instance:

```python
MoneyField = FieldTemplate(places=2, digits=10)

class Account(Record):
    balance = MoneyField()           # Field(places=2, digits=10)
    balance_b = MoneyField(digits=8) # override per-use
```

### Built-in templates

| Name | `places` | `digits` | `signed` |
|---|---|---|---|
| `CurrencyField` | 2 | 10 | `True` |
| `PercentField` | 4 | 3 | `True` |
| `QuantityField` | 3 | 7 | `False` |
| `RateField` | 6 | 2 | `True` |
| `AccountNumberField` | 0 | 12 | `False` |

---

## `ExternalField`

```python
ExternalField(
    field_type: type[T] = object,
    *,
    default: T | None = None,
    default_factory: Callable[[], T] | None = None,
    json_encoder: Callable[[T], object] | None = str,
    json_decoder: Callable[..., T] | None = None,
)
```

Pass-through descriptor for non-decimal values inside a `Record`. The value is stored verbatim; no decimal coercion occurs.

- `default` and `default_factory` are mutually exclusive.
- `json_decoder` defaults to `field_type` when a concrete type is given.
- Calling `.width` raises `TypeError` — no fixed-width support.
- Blocked inside `serializable=True` records.

---

## `Record`

```python
class MyRecord(Record, serializable: bool = False):
    field_a = Field(...)
    field_b = ExternalField(...)
```

Base class for all fixed-decimal record schemas.

### Class-level attributes (set by `__init_subclass__`)

| Name | Type | Description |
|---|---|---|
| `_all_attrs` | `dict[str, Field \| RecordField \| ExternalField]` | All declared descriptors in order |
| `_external_fields` | `dict[str, ExternalField]` | External-only subset |

### Instance methods

| Method | Description |
|---|---|
| `to_dict()` | `dict[str, FixedDecimal \| object]` — all field values |
| `to_json()` | JSON string; `FixedDecimal` → `str`, `ExternalField` → `json_encoder(value)` |
| `from_json(text)` *(classmethod)* | Reconstruct from JSON string |
| `to_string()` | Fixed-width string (requires `serializable=True`) |
| `from_string(line)` *(classmethod)* | Reconstruct from fixed-width string |

### Generated dunder methods

`__init__`, `__repr__`, `__eq__`

---

## `RecordField`

```python
RecordField(record_type: type[R])
```

Descriptor that embeds a nested `Record` as a field. Generic: `RecordField[R]` so the IDE resolves the type of attribute access.

---

## `RoundingStrategy`

```python
class RoundingStrategy(Enum):
    ROUND_HALF_UP    # 2.5 → 3
    ROUND_HALF_DOWN  # 2.5 → 2
    ROUND_HALF_EVEN  # banker's rounding
    ROUND_HALF_ODD   # 2.5 → 3, 3.5 → 3
    ROUND_UP         # away from zero
    ROUND_DOWN       # toward zero (truncate)
    ROUND_CEILING    # toward +∞
    ROUND_FLOOR      # toward -∞
```

---

## `FieldOverflowError`

Raised when a value exceeds the integer `digits` cap of a `Field` or `FixedDecimal`.

```python
class FieldOverflowError(ValueError): ...
```
