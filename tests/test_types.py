import pytest
from fixfield.types import FixedDecimal
from fixfield.rounding import RoundingStrategy


# --- Construction ---

@pytest.mark.parametrize("value, places, expected", [
    ("19.999", 2, "20.00"),
    ("19.994", 2, "19.99"),
    ("1.0",    4, "1.0000"),
    ("0",      2, "0.00"),
    ("-1.005", 2, "-1.01"),   # negative rounding
    ("1",      0, "1"),       # zero decimal places
])
def test_construction_rounds_to_places(value, places, expected):
    fd = FixedDecimal(value, places=places)
    assert str(fd) == expected


@pytest.mark.parametrize("value, places, expected", [
    (0.1,  2, "0.10"),   # float binary imprecision avoided
    (0.2,  2, "0.20"),
    (1.005, 2, "1.01"),  # would fail with Decimal(float) directly
])
def test_float_input_is_safe(value, places, expected):
    fd = FixedDecimal(value, places=places)
    assert str(fd) == expected


# --- Arithmetic ---

@pytest.mark.parametrize("a, b, places, expected", [
    ("1.00",  "2.00",  2, "3.00"),
    ("1.999", "0.001", 2, "2.00"),   # result is rounded
    ("0.10",  "0.20",  2, "0.30"),   # classic float trap
    ("-1.00", "0.50",  2, "-0.50"),
])
def test_add(a, b, places, expected):
    result = FixedDecimal(a, places=places) + FixedDecimal(b, places=places)
    assert str(result) == expected


@pytest.mark.parametrize("a, b, places, expected", [
    ("5.00", "3.00", 2, "2.00"),
    ("1.00", "0.004", 2, "1.00"),   # difference rounds away
    ("0.00", "0.50", 2, "-0.50"),
])
def test_sub(a, b, places, expected):
    result = FixedDecimal(a, places=places) - FixedDecimal(b, places=places)
    assert str(result) == expected


@pytest.mark.parametrize("a, b, places, expected", [
    ("2.00",  "3.00",  2, "6.00"),
    ("1.005", "2.00",  2, "2.02"),   # 1.005 rounds to 1.01 on construction, 1.01 * 2.00 = 2.02
    ("0.10",  "0.10",  2, "0.01"),
])
def test_mul(a, b, places, expected):
    result = FixedDecimal(a, places=places) * FixedDecimal(b, places=places)
    assert str(result) == expected


@pytest.mark.parametrize("a, b, places, expected", [
    ("10.00", "4.00", 2, "2.50"),
    ("1.00",  "3.00", 2, "0.33"),   # repeating decimal rounded to places
    ("2.00",  "3.00", 4, "0.6667"),
])
def test_div(a, b, places, expected):
    result = FixedDecimal(a, places=places) / FixedDecimal(b, places=places)
    assert str(result) == expected


# --- Precision propagation ---

def test_arithmetic_result_inherits_left_places():
    a = FixedDecimal("1.00", places=2)
    b = FixedDecimal("2.00", places=4)
    result = a + b
    assert result.places == 2


def test_arithmetic_result_inherits_left_rounding():
    a = FixedDecimal("1.00", places=2, rounding=RoundingStrategy.ROUND_FLOOR)
    b = FixedDecimal("2.00", places=2, rounding=RoundingStrategy.ROUND_CEILING)
    result = a + b
    assert result.rounding == RoundingStrategy.ROUND_FLOOR


def test_scalar_operand_inherits_left_precision():
    a = FixedDecimal("1.00", places=2)
    result = a + 0.005   # scalar coerced with left's places/rounding
    assert result.places == 2
    assert str(result) == "1.01"


# --- Representation ---

@pytest.mark.parametrize("value, places, expected_str", [
    ("1.5",  2, "1.50"),
    ("100",  0, "100"),
    ("0.1",  4, "0.1000"),
])
def test_str(value, places, expected_str):
    assert str(FixedDecimal(value, places=places)) == expected_str


def test_repr_contains_key_info():
    fd = FixedDecimal("1.50", places=2, rounding=RoundingStrategy.ROUND_HALF_UP)
    r = repr(fd)
    assert "1.50" in r
    assert "places=2" in r
    assert "ROUND_HALF_UP" in r
