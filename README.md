# fixfield

Fixed-decimal arithmetic for Python with per-field precision enforcement.

Inspired by COBOL's `PIC` clause — declare precision once on the field and it is enforced automatically on every assignment and arithmetic result.

```bash
pip install fixfield   # or: uv add fixfield
```

**Requires Python 3.14+**

---

## Quick start

```python
from fixfield import Record, CurrencyField, ExternalField
import uuid

class Invoice(Record):
    invoice_id = ExternalField(uuid.UUID, default_factory=uuid.uuid4,
                               json_encoder=str, json_decoder=uuid.UUID)
    price      = CurrencyField()
    tax        = CurrencyField()
    total      = CurrencyField()

inv = Invoice(price="19.99", tax="0.00")
inv.tax   = inv.price * "0.0825"   # → 1.65
inv.total = inv.price + inv.tax    # → 21.64

print(repr(inv))
# Invoice(invoice_id=UUID('...'), price=19.99, tax=1.65, total=21.64)

print(inv.to_json())
# {"invoice_id": "...", "price": "19.99", "tax": "1.65", "total": "21.64"}

restored = Invoice.from_json(inv.to_json())
assert restored == inv
```

---

## Documentation

📖 **[User Guide](https://charlesreilly0.github.io/fixfield/guide/)** — concepts, all field types, serialisation  
🔎 **[API Reference](https://charlesreilly0.github.io/fixfield/api/)** — every class and parameter  
📋 **[Changelog](https://charlesreilly0.github.io/fixfield/changelog/)**

---

## Why not just use `decimal.Decimal`?

| | `decimal.Decimal` | `fixfield` |
|---|---|---|
| Precision location | Global context or per `.quantize()` | Declared on the field, enforced automatically |
| Per-field rounding | Manual on every result | Declarative |
| Overflow protection | None | `digits` cap + `FieldOverflowError` |
| Domain modelling | Plain values | Named record schema |
| Non-decimal fields | Anything | `ExternalField[T]` |
| Legacy serialisation | Manual | `to_string` / `from_string` |

---

## License

MIT
