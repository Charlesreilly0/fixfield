"""
Domain records for the banking example.

Each Record declares its fields using the shared templates from fields.py.
The Branch is embedded inside Account via RecordField — so a fixed-width
export of an Account carries its branch data as a contiguous block.
"""
import uuid

from fixfield import ExternalField, Record, RecordField
from examples.banking.fields import MoneyField, RateField, IdField


class Branch(Record, serializable=True):
    """A bank branch, identified by a numeric code with a cash reserve."""
    branch_id = IdField(digits=4)          # 0001 – 9999
    reserve   = MoneyField(signed=False)   # branches can't go negative


class Account(Record, serializable=True):
    """
    A customer account.

    Fixed-width layout (used by to_string / from_string):

        branch_id   :  5 chars  (1 sign + 4 digits)
        reserve     : 13 chars  (1 sign + 10 digits + 1 dot + 2 dp)
        account_id  :  9 chars  (1 sign + 8 digits)
        balance     : 13 chars  (1 sign + 10 digits + 1 dot + 2 dp)
        rate        :  7 chars  (1 sign + 2 digits + 1 dot + 4 dp — wait, signed=False, still 1 sign char)

    Total: 47 chars per record line.
    """
    branch     = RecordField(Branch)
    account_id = IdField()
    balance    = MoneyField()
    rate       = RateField()              # annual interest rate, e.g. 0.0350


class Transaction(Record):
    """
    A single debit or credit movement against an account.
    Not serializable (no digits on description — strings live outside fixfield).
    """
    tx_id      = ExternalField(uuid.UUID, default_factory=uuid.uuid4,
                               json_encoder=str, json_decoder=uuid.UUID)
    account_id = IdField()
    amount     = MoneyField()             # positive = credit, negative = debit
    memo       = ExternalField(str, default="")
