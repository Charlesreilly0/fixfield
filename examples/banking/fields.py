"""
Project-wide field templates for the banking example.

Defining templates once here means every Record in the system shares the
same precision rules — change it in one place and it propagates everywhere.
"""
from fixfield import FieldTemplate

# Monetary amounts — 2 dp, ROUND_HALF_UP, signed (balances can go negative)
MoneyField = FieldTemplate(places=2, digits=10, signed=True)

# Interest / fee rates stored as a decimal fraction — e.g. 0.0350 = 3.5 %
RateField = FieldTemplate(places=4, digits=2, signed=False)

# Whole-number identifiers — no decimal, no sign
IdField = FieldTemplate(places=0, digits=8, signed=False)
