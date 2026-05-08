---
layout: page
title: User Guide
permalink: /guide/
---

## Installation

```bash
pip install fixfield
# or with uv
uv add fixfield
```

Requires **Python 3.14+**.

---

## Core concepts

### `FixedDecimal`

A scalar decimal value locked to a declared precision. Arithmetic always rounds the result to the **left operand's** precision.

```python
from fixfield import FixedDecimal

price = FixedDecimal("19.999", places=2)  # rounded to 19.00 on construction
str(price)   # "20.00"

result = price + FixedDecimal("1.005", places=4)
result.places   # 2  — left operand wins
str(result)     # "21.00"
```

Float inputs are converted via `str()` to avoid binary imprecision:

```python
FixedDecimal(0.1 + 0.2, places=2)   # "0.30"  ✓
```

---

### `Field`

A descriptor that enforces precision on every assignment. Declare it inside a `Record`.

```python
from fixfield import Field, RoundingStrategy

class Invoice(Record):
    price    = Field(places=2)
    tax_rate = Field(places=4, rounding=RoundingStrategy.ROUND_FLOOR)
    total    = Field(places=2, default="0.00")
    capped   = Field(places=2, digits=5)          # raises FieldOverflowError above 99999.99
```

| Parameter | Default | Description |
|---|---|---|
| `places` | `2` | Decimal places |
| `rounding` | `ROUND_HALF_UP` | Rounding strategy |
| `default` | `None` | Value when not supplied to `__init__` |
| `digits` | `None` | Max integer digits (enables overflow protection and `to_string`) |
| `signed` | `True` | Set `False` to reject negative values |

---

### `Record`

A structured collection of `Field` descriptors. Generates `__init__`, `__repr__`, and `__eq__` automatically. Fields are processed in declaration order.

```python
from fixfield import Record, Field

class Payment(Record):
    amount = Field(places=2, digits=7)
    fee    = Field(places=2, digits=4)
    net    = Field(places=2, digits=7)

p = Payment(amount="1000.00", fee="2.50")
p.net = p.amount - p.fee

print(repr(p))     # Payment(amount=1000.00, fee=2.50, net=997.50)
p.to_dict()        # {"amount": FixedDecimal(...), ...}
```

Pass `serializable=True` to enable `to_string` / `from_string` and require `digits` on all fields:

```python
class Payment(Record, serializable=True):
    amount = Field(places=2, digits=7)
    fee    = Field(places=2, digits=4)
```

---

### `FieldTemplate`

A reusable preset for a field. The built-in templates are ready to use:

| Template | `places` | `digits` | `signed` |
|---|---|---|---|
| `CurrencyField()` | 2 | 10 | True |
| `PercentField()` | 4 | 3 | True |
| `QuantityField()` | 3 | 7 | False |
| `RateField()` | 6 | 2 | True |
| `AccountNumberField()` | 0 | 12 | False |

All built-in templates are `FieldTemplate` instances, so you can call them like `Field`:

```python
from fixfield import CurrencyField, PercentField

class Invoice(Record):
    price    = CurrencyField()
    tax_rate = PercentField()
    total    = CurrencyField()
```

Define your own:

```python
from fixfield import FieldTemplate

MoneyField = FieldTemplate(places=2, digits=10, signed=True)
RateField  = FieldTemplate(places=6, digits=2,  signed=False)
```

---

### `RecordField`

Embed a nested `Record` as a single field. Its fields participate in `to_string` / `from_string` as a contiguous block.

```python
from fixfield import Record, Field, RecordField

class Address(Record):
    zip_code = Field(places=0, digits=5)

class Customer(Record):
    customer_id = Field(places=0, digits=6)
    address     = RecordField(Address)

c = Customer(customer_id="42", address=Address(zip_code="90210"))
line = c.to_string()                   # "    42 90210"
parsed = Customer.from_string(line)
str(parsed.address.zip_code)           # "90210"
```

`RecordField[T]` is generic — your IDE knows `c.address` is an `Address`.

---

### `ExternalField`

A pass-through descriptor for **non-decimal** values (UUIDs, strings, enums, plain ints, …) inside a `Record`. Participates in `__init__`, `__repr__`, `__eq__`, `to_dict()`, `to_json()`, and `from_json()`, but **not** in `to_string` / `from_string`.

```python
import uuid
from fixfield import Record, ExternalField, CurrencyField

class Order(Record):
    order_id  = ExternalField(uuid.UUID, default_factory=uuid.uuid4,
                              json_encoder=str, json_decoder=uuid.UUID)
    reference = ExternalField(str, default="")
    total     = CurrencyField()

o = Order(reference="ORD-001", total="99.99")
print(type(o.order_id))    # <class 'uuid.UUID'>
print(o.to_json())
# {"order_id": "...", "reference": "ORD-001", "total": "99.99"}

restored = Order.from_json(o.to_json())
assert restored.order_id == o.order_id
```

| Parameter | Default | Description |
|---|---|---|
| `field_type` | `object` | Expected Python type; checked on every `__set__` |
| `default` | `None` | Static default value |
| `default_factory` | `None` | Callable invoked once per instance to produce a default |
| `json_encoder` | `str` | Serialises the value for `to_json()` |
| `json_decoder` | `field_type` | Deserialises the JSON value in `from_json()` |

`default` and `default_factory` are mutually exclusive.

`ExternalField` is blocked inside `serializable=True` records.

---

### `RoundingStrategy`

```python
from fixfield import RoundingStrategy

RoundingStrategy.ROUND_HALF_UP    # 2.5 → 3  (COBOL ROUNDED default)
RoundingStrategy.ROUND_HALF_DOWN  # 2.5 → 2
RoundingStrategy.ROUND_HALF_EVEN  # 2.5 → 2, 3.5 → 4  (banker's rounding)
RoundingStrategy.ROUND_HALF_ODD   # 2.5 → 3, 3.5 → 3
RoundingStrategy.ROUND_UP         # always away from zero
RoundingStrategy.ROUND_DOWN       # always toward zero (truncate)
RoundingStrategy.ROUND_CEILING    # toward +∞
RoundingStrategy.ROUND_FLOOR      # toward -∞
```

---

## Fixed-width serialisation

When every `Field` has `digits` set, a `Record` can be serialised to and from a fixed-width string — useful for mainframe flat files and legacy EDI formats. Use `serializable=True` to opt in (it checks all fields at class-definition time).

```python
class CustomerRecord(Record, serializable=True):
    customer_id = Field(places=0, digits=6)   # 7 chars:  " 123456"
    balance     = Field(places=2, digits=8)   # 11 chars: "  1234.56"

rec = CustomerRecord(customer_id="123456", balance="1234.56")
line = rec.to_string()                # " 123456  1234.56"
parsed = CustomerRecord.from_string(line)
assert parsed == rec
```

Field width formula: `1 (sign) + digits + (1 + places if places > 0 else 0)`

---

## JSON serialisation

```python
import json
from fixfield import Record, CurrencyField

class Invoice(Record):
    price = CurrencyField()
    total = CurrencyField()

inv = Invoice(price="19.99", total="21.64")
payload = inv.to_json()
# '{"price": "19.99", "total": "21.64"}'

restored = Invoice.from_json(payload)
assert restored == inv
```

Nested `RecordField` values are serialised inline. `ExternalField` values use their configured `json_encoder` / `json_decoder`.

---

## Overflow protection

```python
from fixfield import Field, Record, FieldOverflowError

class Account(Record):
    balance = Field(places=2, digits=5)   # max 99999.99

a = Account()
a.balance = "99999.99"    # ✓
a.balance = "100000.00"   # raises FieldOverflowError
```

---

## Why not just use `decimal.Decimal`?

| | `decimal.Decimal` | `fixfield` |
|---|---|---|
| Precision location | Global context or per `.quantize()` | Declared on the field, enforced automatically |
| Per-field rounding | Manual on every result | Declarative |
| Domain modelling | Plain values | Named record schema |
| Non-decimal fields | Anything | `ExternalField` |
| Legacy serialisation | Manual | `to_string` / `from_string` |

---

## Dataclass integration

For users who prefer `@dataclass`, use `FixedDecimal` directly:

```python
from dataclasses import dataclass, field
from fixfield import FixedDecimal

@dataclass
class LineItem:
    price:    FixedDecimal = field(default_factory=lambda: FixedDecimal(0, places=2))
    quantity: int = 1

    def __post_init__(self):
        if not isinstance(self.price, FixedDecimal):
            self.price = FixedDecimal(self.price, places=2)

    @property
    def total(self) -> FixedDecimal:
        return self.price * self.quantity
```

For full per-field precision enforcement without boilerplate, use `Record` instead.
