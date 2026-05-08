import pytest
from fixfield.field import Field
from fixfield.record import Record
from fixfield.types import FixedDecimal
from fixfield.rounding import RoundingStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class SimpleRecord(Record):
    price    = Field(places=2)
    tax_rate = Field(places=4)
    total    = Field(places=2, default="0.00")


class RoundingRecord(Record):
    amount = Field(places=2, rounding=RoundingStrategy.ROUND_FLOOR)


# ---------------------------------------------------------------------------
# Field — descriptor protocol
# ---------------------------------------------------------------------------

def test_field_set_name():
    assert SimpleRecord.price._attr == "_field_price"
    assert SimpleRecord.tax_rate._attr == "_field_tax_rate"


def test_field_class_access_returns_field():
    assert isinstance(SimpleRecord.price, Field)


def test_field_set_coerces_string():
    r = SimpleRecord(price="19.999")
    assert str(r.price) == "20.00"


def test_field_set_coerces_int():
    r = SimpleRecord(price=5)
    assert str(r.price) == "5.00"


def test_field_set_coerces_float():
    r = SimpleRecord(price=0.1 + 0.2)
    assert str(r.price) == "0.30"


def test_field_set_coerces_fixed_decimal_with_different_places():
    fd = FixedDecimal("19.9999", places=4)
    r = SimpleRecord(price=fd)
    # Field(places=2) should re-apply its own precision
    assert r.price.places == 2
    assert str(r.price) == "20.00"


def test_field_assignment_after_init():
    r = SimpleRecord(price="10.00")
    r.price = "15.555"
    assert str(r.price) == "15.56"


def test_field_respects_rounding_strategy():
    r = RoundingRecord(amount="1.999")
    assert str(r.amount) == "1.99"   # FLOOR rounds down


def test_field_unset_returns_zero():
    r = SimpleRecord()
    assert str(r.price) == "0.00"


def test_field_default_is_used_when_not_provided():
    r = SimpleRecord()
    assert str(r.total) == "0.00"


def test_field_default_does_not_share_state_between_instances():
    r1 = SimpleRecord()
    r2 = SimpleRecord()
    r1.total = "99.99"
    assert str(r2.total) == "0.00"


# ---------------------------------------------------------------------------
# Field — precision
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("places, value, expected", [
    (0, "1.5",    "2"),
    (2, "1.005",  "1.01"),
    (4, "1.00005","1.0001"),
])
def test_field_precision_at_various_places(places, value, expected):
    class R(Record):
        x = Field(places=places)
    r = R(x=value)
    assert str(r.x) == expected


# ---------------------------------------------------------------------------
# Record — init
# ---------------------------------------------------------------------------

def test_record_init_keyword_args():
    r = SimpleRecord(price="10.00", tax_rate="0.0825")
    assert str(r.price)    == "10.00"
    assert str(r.tax_rate) == "0.0825"


def test_record_init_partial_kwargs():
    r = SimpleRecord(price="9.99")
    assert str(r.price)    == "9.99"
    assert str(r.tax_rate) == "0.0000"   # unset — zero at field's precision


def test_record_init_empty():
    r = SimpleRecord()
    assert str(r.price)    == "0.00"
    assert str(r.tax_rate) == "0.0000"
    assert str(r.total)    == "0.00"


# ---------------------------------------------------------------------------
# Record — repr and eq
# ---------------------------------------------------------------------------

def test_record_repr_contains_field_values():
    r = SimpleRecord(price="19.99", tax_rate="0.0825")
    text = repr(r)
    assert "SimpleRecord" in text
    assert "19.99" in text
    assert "0.0825" in text


def test_record_eq_same_values():
    r1 = SimpleRecord(price="10.00", tax_rate="0.0500")
    r2 = SimpleRecord(price="10.00", tax_rate="0.0500")
    assert r1 == r2


def test_record_eq_different_values():
    r1 = SimpleRecord(price="10.00")
    r2 = SimpleRecord(price="20.00")
    assert r1 != r2


def test_record_eq_different_types():
    r = SimpleRecord(price="10.00")
    assert r != "not a record"


# ---------------------------------------------------------------------------
# Record — to_dict
# ---------------------------------------------------------------------------

def test_record_to_dict_returns_fixed_decimals():
    r = SimpleRecord(price="10.00", tax_rate="0.0825")
    d = r.to_dict()
    assert set(d.keys()) == {"price", "tax_rate", "total"}
    assert isinstance(d["price"], FixedDecimal)
    assert str(d["price"]) == "10.00"


# ---------------------------------------------------------------------------
# Record — field ordering
# ---------------------------------------------------------------------------

def test_record_fields_in_declaration_order():
    assert list(SimpleRecord._fields.keys()) == ["price", "tax_rate", "total"]


# ---------------------------------------------------------------------------
# Record — arithmetic across fields
# ---------------------------------------------------------------------------

def test_record_field_arithmetic():
    r = SimpleRecord(price="100.00", tax_rate="0.0825")
    r.total = r.price * r.tax_rate
    assert str(r.total) == "8.25"


def test_record_field_arithmetic_precision_from_field():
    # total is places=2, even though intermediate result has more digits
    r = SimpleRecord(price="100.00", tax_rate="0.1005")
    r.total = r.price * r.tax_rate
    assert r.total.places == 2
    assert str(r.total) == "10.05"
