# fixfield

Fixed-decimal arithmetic for Python with per-field precision enforcement.

Inspired by COBOL's `PIC` clause — declare precision once on the field, and it is enforced automatically on every assignment and arithmetic result.

---

## Installation

```bash
uv add fixfield
# or
pip install fixfield
```

---

## Quick Start

```python
from fixfield import Record, Field, RoundingStrategy

class Invoice(Record):
    price    = Field(places=2)
    tax_rate = Field(places=4)
    tax      = Field(places=2)
    total    = Field(places=2)

inv = Invoice(price="19.99", tax_rate="0.0825")
inv.tax   = inv.price * inv.tax_rate   # 1.649175 → rounded to 1.65
inv.total = inv.price + inv.tax        # 21.64

print(inv.total)   # "21.64"
print(repr(inv))   # Invoice(price=19.99, tax_rate=0.0825, tax=1.65, total=21.64)
```

---

## Why Not Just Use `decimal.Decimal`?

| | `decimal.Decimal` | `fixfield` |
|---|---|---|
| Precision location | Global context or per `.quantize()` call | Declared on the field, enforced automatically |
| Rounding enforcement | Manual on every result | Automatic on every assignment |
| Per-field rounding strategy | Manual | Declarative |
| Domain modelling | Plain values | Named record schema |

With `decimal` you must call `.quantize()` on every result or silently lose precision. With `fixfield` the field declaration is the single source of truth.

---

## Core Concepts

### `FixedDecimal`

A scalar decimal value locked to a declared precision.

```python
from fixfield import FixedDecimal, RoundingStrategy

price = FixedDecimal("19.999", places=2)
str(price)   # "20.00" — rounded on construction

# Arithmetic preserves left operand's precision
result = price + FixedDecimal("1.005", places=4)
result.places     # 2  (left operand wins)
str(result)       # "21.00"

# Comparisons work naturally
price > FixedDecimal("10.00")   # True
price == "20.00"                # True

# Unary operators
str(-price)        # "-20.00"
str(abs(-price))   # "20.00"
```

Float inputs are automatically converted via `str` to avoid binary imprecision:

```python
FixedDecimal(0.1 + 0.2, places=2)   # "0.30" not "0.30000000000000004"
```

### `Field`

A descriptor that enforces precision on a class attribute. Used inside a `Record`.

```python
from fixfield import Field, RoundingStrategy

price    = Field(places=2)                                    # default ROUND_HALF_UP
tax_rate = Field(places=4, rounding=RoundingStrategy.ROUND_FLOOR)
total    = Field(places=2, default="0.00")
capped   = Field(places=2, digits=5)                          # max 99999.99
```

| Parameter | Default | Description |
|---|---|---|
| `places` | `2` | Decimal places to keep |
| `rounding` | `ROUND_HALF_UP` | Rounding strategy on assignment |
| `default` | `None` | Default value (zero if not set) |
| `digits` | `None` | Max integer digits — raises `FieldOverflowError` if exceeded |

### `Record`

A structured collection of `Field` descriptors. Generates `__init__`, `__repr__`, and `__eq__` automatically.

> **Field ordering** relies on Python's guaranteed `dict` insertion order (Python 3.7+). Fields are serialised to and from fixed-width strings in the order they are declared in the class body.

```python
from fixfield import Record, Field

class Payment(Record):
    amount     = Field(places=2, digits=7)   # up to 9999999.99
    fee        = Field(places=2, digits=4)
    net        = Field(places=2, digits=7)

p = Payment(amount="1000.00", fee="2.50")
p.net = p.amount - p.fee

print(p)          # Payment(amount=1000.00, fee=2.50, net=997.50)
p.to_dict()       # {"amount": FixedDecimal(...), "fee": ..., "net": ...}
```

### `RecordField`

Embed a nested `Record` as a field inside another `Record`. The nested record's fields participate in `to_string`/`from_string` as a contiguous block.

```python
from fixfield import Record, Field, RecordField

class Address(Record):
    zip_code = Field(places=0, digits=5)
    state    = Field(places=0, digits=2)

class Customer(Record):
    customer_id = Field(places=0, digits=6)
    address     = RecordField(Address)

c = Customer(customer_id="42", address=Address(zip_code="90210", state="6"))
line = c.to_string()                        # "    42 90210 6"
parsed = Customer.from_string(line)
str(parsed.address.zip_code)                # "90210"
```

`RecordField` is generic: `RecordField[Address]` so your IDE knows that `c.address` is an `Address`, not just a `Record`.

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

## Fixed-Width Serialization

When every `Field` has `digits` set, records can be serialized to and from fixed-width strings — useful for mainframe flat files and legacy EDI formats.

```python
class CustomerRecord(Record):
    customer_id = Field(places=0, digits=6)    # 7 chars:  " 123456"
    balance     = Field(places=2, digits=8)    # 11 chars: "  99999.99"

rec = CustomerRecord(customer_id="123456", balance="99999.99")
line = rec.to_string()             # " 123456  99999.99"

parsed = CustomerRecord.from_string(line)
parsed.balance == rec.balance      # True
```

Field width formula: `1 (sign) + digits + (1 + places if places > 0 else 0)`

---

## Overflow Protection

```python
from fixfield import Field, Record, FieldOverflowError

class Account(Record):
    balance = Field(places=2, digits=5)   # max 99999.99

a = Account()
a.balance = "99999.99"   # ok
a.balance = "100000.00"  # raises FieldOverflowError
```

---

## Dataclass Integration

For users who prefer `@dataclass`, use `FixedDecimal` directly and coerce values in `__post_init__`:

```python
from dataclasses import dataclass, field
from fixfield import FixedDecimal, RoundingStrategy

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

For full precision enforcement without `__post_init__` boilerplate, use `Record` instead.

---

## License

MIT
