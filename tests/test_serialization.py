import pytest
from fixfield import Field, Record


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FixedRecord(Record):
    customer_id = Field(places=0, digits=6)    # width = 1+6       = 7
    balance     = Field(places=2, digits=8)    # width = 1+8+1+2   = 12
    code        = Field(places=0, digits=2)    # width = 1+2       = 3


# ---------------------------------------------------------------------------
# Field.width
# ---------------------------------------------------------------------------

def test_field_width_no_decimal_places():
    f = Field(places=0, digits=6)
    assert f.width == 7   # 1 (sign) + 6


def test_field_width_with_decimal_places():
    f = Field(places=2, digits=8)
    assert f.width == 12  # 1 (sign) + 8 + 1 (.) + 2


def test_field_width_requires_digits():
    f = Field(places=2)   # no digits set
    with pytest.raises(ValueError, match="digits"):
        _ = f.width


@pytest.mark.parametrize("digits, places, expected_width", [
    (5, 2,  9),    # 1+5+1+2
    (3, 0,  4),    # 1+3
    (1, 4,  7),    # 1+1+1+4
    (10, 0, 11),   # 1+10
])
def test_field_width_parametrised(digits, places, expected_width):
    assert Field(places=places, digits=digits).width == expected_width


# ---------------------------------------------------------------------------
# Record.to_string
# ---------------------------------------------------------------------------

def test_to_string_positive_values():
    r = FixedRecord(customer_id="123456", balance="99999.99", code="42")
    line = r.to_string()
    assert len(line) == 7 + 12 + 3   # total width = 22
    # " 123456" + "    99999.99" + " 42"
    assert line == " 123456    99999.99 42"


def test_to_string_negative_balance():
    r = FixedRecord(customer_id="1", balance="-250.50", code="1")
    line = r.to_string()
    assert "-250.50" in line


def test_to_string_zero_values():
    r = FixedRecord()
    line = r.to_string()
    assert len(line) == 7 + 12 + 3


def test_to_string_raises_without_digits():
    class NoDigits(Record):
        amount = Field(places=2)   # no digits

    r = NoDigits(amount="1.00")
    with pytest.raises(ValueError, match="digits"):
        r.to_string()


# ---------------------------------------------------------------------------
# Record.from_string
# ---------------------------------------------------------------------------

def test_round_trip():
    r = FixedRecord(customer_id="123456", balance="99999.99", code="42")
    parsed = FixedRecord.from_string(r.to_string())
    assert parsed == r


def test_from_string_preserves_precision():
    r = FixedRecord(customer_id="1", balance="1234.56", code="7")
    parsed: FixedRecord = FixedRecord.from_string(r.to_string())  # type: ignore[assignment]
    assert str(parsed.balance) == "1234.56"
    assert parsed.balance.places == 2


def test_from_string_negative_value():
    r = FixedRecord(customer_id="999999", balance="-9999.99", code="99")
    parsed: FixedRecord = FixedRecord.from_string(r.to_string())  # type: ignore[assignment]
    assert str(parsed.balance) == "-9999.99"


@pytest.mark.parametrize("customer_id, balance, code", [
    ("1",      "0.01",    "1"),
    ("999999", "99999.99","99"),
    ("0",      "-0.01",   "0"),
])
def test_round_trip_parametrised(customer_id, balance, code):
    r = FixedRecord(customer_id=customer_id, balance=balance, code=code)
    assert FixedRecord.from_string(r.to_string()) == r


def test_from_string_raises_on_short_input():
    with pytest.raises(ValueError, match="expects at least"):
        FixedRecord.from_string("tooshort")


# ---------------------------------------------------------------------------
# py.typed marker
# ---------------------------------------------------------------------------

def test_py_typed_marker_exists():
    import importlib.resources
    ref = importlib.resources.files("fixfield").joinpath("py.typed")
    assert ref.is_file()
