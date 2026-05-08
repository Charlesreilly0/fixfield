---
layout: home
title: fixfield
---

# fixfield

Fixed-decimal arithmetic for Python with per-field precision enforcement.

Inspired by COBOL's `PIC` clause — declare precision once on the field and it is enforced automatically on every assignment and arithmetic result.

```bash
pip install fixfield   # or: uv add fixfield
```

```python
from fixfield import Record, CurrencyField

class Invoice(Record):
    price = CurrencyField()
    tax   = CurrencyField()
    total = CurrencyField()

inv = Invoice(price="19.99", tax="0.00")
inv.tax   = inv.price * "0.0825"   # → 1.65
inv.total = inv.price + inv.tax    # → 21.64
print(repr(inv))
# Invoice(price=19.99, tax=1.65, total=21.64)
```

**Python 3.14+ required.**

→ [User Guide](guide.md) · [API Reference](api.md) · [Changelog](changelog.md) · [GitHub](https://github.com/Charlesreilly0/fixfield) · [PyPI](https://pypi.org/project/fixfield/)
