"""Tests for RecordField — nested Record composition."""
import pytest
from fixfield import Field, Record, RecordField


# ---------------------------------------------------------------------------
# Fixture records
# ---------------------------------------------------------------------------

class Address(Record):
    zip_code = Field(places=0, digits=5)
    zone     = Field(places=0, digits=2)


class Customer(Record):
    customer_id = Field(places=0, digits=6)
    address     = RecordField(Address)


class NestedSerial(Record):
    """All fields have digits so to_string / from_string work end-to-end."""
    code    = Field(places=0, digits=3)   # 4 chars
    address = RecordField(Address)        # zip=6, zone=3 → 9 chars


# ---------------------------------------------------------------------------
# Basic construction and access
# ---------------------------------------------------------------------------

def test_recordfield_class_access_returns_descriptor():
    assert isinstance(Customer.address, RecordField)


def test_recordfield_default_returns_empty_nested_record():
    c = Customer(customer_id="1")
    assert isinstance(c.address, Address)


def test_recordfield_set_stores_instance():
    addr = Address(zip_code="90210", zone="1")
    c = Customer(customer_id="42", address=addr)
    assert str(c.address.zip_code) == "90210"
    assert str(c.address.zone) == "1"


def test_recordfield_set_via_assignment():
    c = Customer(customer_id="1")
    c.address = Address(zip_code="10001", zone="5")
    assert str(c.address.zip_code) == "10001"


def test_recordfield_rejects_wrong_type():
    c = Customer(customer_id="1")
    with pytest.raises(TypeError, match="Expected Address"):
        c.address = "not an address"  # type: ignore[assignment]


def test_recordfield_instances_are_independent():
    a = Address(zip_code="11111", zone="1")
    b = Address(zip_code="22222", zone="2")
    c1 = Customer(customer_id="1", address=a)
    c2 = Customer(customer_id="2", address=b)
    assert str(c1.address.zip_code) == "11111"
    assert str(c2.address.zip_code) == "22222"


# ---------------------------------------------------------------------------
# width property
# ---------------------------------------------------------------------------

def test_recordfield_width_equals_nested_record_total_width():
    # zip_code: 1+5 = 6,  zone: 1+2 = 3  → total 9
    assert Customer.address.width == 9


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------

def test_recordfield_repr():
    assert repr(Customer.address) == "RecordField(Address)"


def test_customer_repr_includes_nested():
    addr = Address(zip_code="90210", zone="3")
    c = Customer(customer_id="7", address=addr)
    r = repr(c)
    assert "90210" in r
    assert "3" in r


# ---------------------------------------------------------------------------
# __eq__
# ---------------------------------------------------------------------------

def test_customer_eq_same_values():
    addr1 = Address(zip_code="90210", zone="1")
    addr2 = Address(zip_code="90210", zone="1")
    c1 = Customer(customer_id="1", address=addr1)
    c2 = Customer(customer_id="1", address=addr2)
    assert c1 == c2


def test_customer_eq_different_nested():
    c1 = Customer(customer_id="1", address=Address(zip_code="90210", zone="1"))
    c2 = Customer(customer_id="1", address=Address(zip_code="99999", zone="1"))
    assert c1 != c2


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------

def test_to_dict_includes_nested_record():
    addr = Address(zip_code="10001", zone="2")
    c = Customer(customer_id="5", address=addr)
    d = c.to_dict()
    assert "address" in d
    assert isinstance(d["address"], Address)


# ---------------------------------------------------------------------------
# Fixed-width serialisation
# ---------------------------------------------------------------------------

def test_nested_to_string():
    rec = NestedSerial(
        code="42",
        address=Address(zip_code="90210", zone="7"),
    )
    s = rec.to_string()
    # code: 4 chars " 42" → rjust(4) = "  42"
    # zip_code: 6 chars → "90210".rjust(6) = " 90210"
    # zone: 3 chars → "7".rjust(3) = "  7"
    assert s == "  42 90210  7"


def test_nested_from_string_round_trip():
    rec = NestedSerial(
        code="7",
        address=Address(zip_code="12345", zone="9"),
    )
    line = rec.to_string()
    parsed = NestedSerial.from_string(line)
    assert str(parsed.code) == "7"
    assert str(parsed.address.zip_code) == "12345"
    assert str(parsed.address.zone) == "9"


def test_nested_from_string_raises_on_short_input():
    with pytest.raises(ValueError, match="expects at least"):
        NestedSerial.from_string("too short")
