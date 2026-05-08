"""
Tests covering the four feedback items:
  1. serializable=True validates digits at class-definition time
  2. signed=False rejects negative values
  3. CurrencyField / PercentField convenience factories
  4. to_json / from_json round-trips
"""
import json
import pytest
from fixfield import (
    Field, Record, RecordField,
    CurrencyField, PercentField,
    FieldOverflowError,
)


# ---------------------------------------------------------------------------
# 1. serializable=True — digits validated at class definition
# ---------------------------------------------------------------------------

def test_serializable_ok_when_all_fields_have_digits():
    """Should not raise when every Field has digits set."""
    class GoodRecord(Record, serializable=True):
        amount = Field(places=2, digits=8)
        code   = Field(places=0, digits=3)


def test_serializable_raises_when_digits_missing():
    with pytest.raises(TypeError, match="missing 'digits'"):
        class BadRecord(Record, serializable=True):
            amount = Field(places=2, digits=8)
            code   = Field(places=0)          # no digits!


def test_serializable_reports_all_missing_fields():
    with pytest.raises(TypeError, match="amount") as exc_info:
        class BadRecord(Record, serializable=True):
            amount = Field(places=2)
            code   = Field(places=0)
    assert "code" in str(exc_info.value)


def test_non_serializable_record_does_not_require_digits():
    """Without serializable=True there should be no error at class definition."""
    class LazyRecord(Record):
        amount = Field(places=2)   # no digits — fine


def test_serializable_ignores_recordfields():
    """RecordField entries are not checked directly (nested record is responsible)."""
    class Inner(Record, serializable=True):
        code = Field(places=0, digits=3)

    class Outer(Record, serializable=True):
        value   = Field(places=2, digits=8)
        nested  = RecordField(Inner)


# ---------------------------------------------------------------------------
# 2. signed=False — rejects negative values
# ---------------------------------------------------------------------------

class UnsignedRecord(Record):
    balance = Field(places=2, digits=8, signed=False)


def test_unsigned_field_accepts_zero():
    r = UnsignedRecord(balance="0.00")
    assert str(r.balance) == "0.00"


def test_unsigned_field_accepts_positive():
    r = UnsignedRecord(balance="99.99")
    assert str(r.balance) == "99.99"


def test_unsigned_field_rejects_negative_string():
    with pytest.raises(FieldOverflowError, match="unsigned"):
        UnsignedRecord(balance="-0.01")


def test_unsigned_field_rejects_negative_assignment():
    r = UnsignedRecord(balance="10.00")
    with pytest.raises(FieldOverflowError, match="unsigned"):
        r.balance = "-5.00"


def test_signed_field_default_accepts_negative():
    class SignedRecord(Record):
        balance = Field(places=2)
    r = SignedRecord(balance="-99.99")
    assert str(r.balance) == "-99.99"


# ---------------------------------------------------------------------------
# 3. CurrencyField / PercentField
# ---------------------------------------------------------------------------

class PriceRecord(Record):
    price    = CurrencyField(digits=6)
    tax_rate = PercentField()
    total    = CurrencyField(digits=6)


def test_currency_field_places_is_2():
    assert PriceRecord.price.places == 2


def test_currency_field_digits_respected():
    assert PriceRecord.price.digits == 6


def test_currency_field_rounds_to_2dp():
    r = PriceRecord(price="19.999")
    assert str(r.price) == "20.00"


def test_percent_field_places_is_4():
    assert PriceRecord.tax_rate.places == 4


def test_percent_field_default_digits():
    assert PriceRecord.tax_rate.digits == 3


def test_percent_field_rounds_to_4dp():
    r = PriceRecord(tax_rate="0.08259")
    assert str(r.tax_rate) == "0.0826"


def test_currency_field_signed_param():
    class Ledger(Record):
        debit = CurrencyField(digits=6, signed=False)
    with pytest.raises(FieldOverflowError):
        Ledger(debit="-1.00")


# ---------------------------------------------------------------------------
# 4. to_json / from_json
# ---------------------------------------------------------------------------

class Invoice(Record):
    price    = Field(places=2)
    tax_rate = Field(places=4)
    total    = Field(places=2)


def test_to_json_produces_valid_json():
    inv = Invoice(price="19.99", tax_rate="0.0825", total="21.64")
    data = json.loads(inv.to_json())
    assert data["price"] == "19.99"
    assert data["tax_rate"] == "0.0825"
    assert data["total"] == "21.64"


def test_from_json_round_trip():
    inv = Invoice(price="19.99", tax_rate="0.0825", total="21.64")
    restored = Invoice.from_json(inv.to_json())
    assert inv == restored


def test_from_json_partial_fields():
    """from_json should accept JSON with only some fields set."""
    restored = Invoice.from_json('{"price": "9.99"}')
    assert str(restored.price) == "9.99"
    assert str(restored.total) == "0.00"   # default


def test_to_json_nested_record():
    class Address(Record):
        zip_code = Field(places=0, digits=5)

    class Customer(Record):
        customer_id = Field(places=0, digits=6)
        address     = RecordField(Address)

    c = Customer(
        customer_id="42",
        address=Address(zip_code="90210"),
    )
    data = json.loads(c.to_json())
    assert data["customer_id"] == "42"
    assert data["address"]["zip_code"] == "90210"


def test_from_json_nested_record():
    class Address(Record):
        zip_code = Field(places=0, digits=5)

    class Customer(Record):
        customer_id = Field(places=0, digits=6)
        address     = RecordField(Address)

    payload = '{"customer_id": "42", "address": {"zip_code": "90210"}}'
    c = Customer.from_json(payload)
    assert str(c.customer_id) == "42"
    assert str(c.address.zip_code) == "90210"


def test_from_json_raises_on_wrong_nested_type():
    class Address(Record):
        zip_code = Field(places=0, digits=5)

    class Customer(Record):
        customer_id = Field(places=0, digits=6)
        address     = RecordField(Address)

    with pytest.raises(ValueError, match="JSON object"):
        Customer.from_json('{"customer_id": "1", "address": "bad"}')
