import pytest
from fixfield import (
    FixedDecimal,
    Field,
    Record,
    FieldOverflowError,
    RoundingStrategy,
)


# ---------------------------------------------------------------------------
# Comparison operators
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("a, b", [
    ("1.00", "1.00"),
    ("0.00", "0"),
    ("-1.50", "-1.50"),
])
def test_eq_true(a, b):
    assert FixedDecimal(a, places=2) == FixedDecimal(b, places=2)


def test_eq_with_raw_number():
    assert FixedDecimal("1.50", places=2) == "1.50"
    assert FixedDecimal("1.50", places=2) == 1.5
    assert FixedDecimal("1.00", places=2) == 1


def test_eq_returns_not_implemented_for_unrelated_type():
    assert (FixedDecimal("1.00", places=2) == object()) is False


@pytest.mark.parametrize("a, op, b, expected", [
    ("1.00", "<",  "2.00", True),
    ("2.00", "<",  "1.00", False),
    ("1.00", "<=", "1.00", True),
    ("2.00", ">",  "1.00", True),
    ("1.00", ">=", "1.00", True),
    ("-1.00", "<", "0.00", True),
])
def test_ordering(a, op, b, expected):
    fa = FixedDecimal(a, places=2)
    fb = FixedDecimal(b, places=2)
    ops = {
        "<":  fa.__lt__,
        "<=": fa.__le__,
        ">":  fa.__gt__,
        ">=": fa.__ge__,
    }
    assert ops[op](fb) is expected


def test_ordering_with_raw_number():
    fd = FixedDecimal("1.50", places=2)
    assert fd < 2
    assert fd > "1.00"
    assert fd <= 1.5


def test_hash_differs_for_different_places():
    a = FixedDecimal("1.00", places=2)
    b = FixedDecimal("1.00", places=4)
    assert hash(a) != hash(b)
    assert a != b   # precision-sensitive equality


def test_hash_equal_for_same_places():
    a = FixedDecimal("1.00", places=2)
    b = FixedDecimal("1.00", places=2)
    assert hash(a) == hash(b)
    assert a == b


# ---------------------------------------------------------------------------
# Unary operators
# ---------------------------------------------------------------------------

def test_neg():
    assert str(-FixedDecimal("1.50", places=2)) == "-1.50"


def test_neg_preserves_precision():
    fd = -FixedDecimal("1.50", places=4, rounding=RoundingStrategy.ROUND_FLOOR)
    assert fd.places == 4
    assert fd.rounding == RoundingStrategy.ROUND_FLOOR


def test_abs_positive():
    assert str(abs(FixedDecimal("1.50", places=2))) == "1.50"


def test_abs_negative():
    assert str(abs(FixedDecimal("-1.50", places=2))) == "1.50"


# ---------------------------------------------------------------------------
# Overflow / digits
# ---------------------------------------------------------------------------

def test_overflow_on_construction():
    with pytest.raises(FieldOverflowError):
        FixedDecimal("100.00", places=2, digits=2)   # 100 has 3 integer digits


def test_overflow_at_boundary():
    # 99.99 → 2 integer digits, fits digits=2
    fd = FixedDecimal("99.99", places=2, digits=2)
    assert str(fd) == "99.99"


def test_overflow_just_over_boundary():
    with pytest.raises(FieldOverflowError):
        FixedDecimal("100.00", places=2, digits=2)


def test_overflow_negative_value():
    with pytest.raises(FieldOverflowError):
        FixedDecimal("-100.00", places=2, digits=2)


def test_overflow_propagates_through_arithmetic():
    a = FixedDecimal("90.00", places=2, digits=2)
    b = FixedDecimal("20.00", places=2, digits=2)
    with pytest.raises(FieldOverflowError):
        _ = a + b   # 110.00 exceeds 2 integer digits


def test_no_overflow_when_digits_is_none():
    # default behaviour — no cap
    fd = FixedDecimal("9999999999", places=2)
    assert str(fd) == "9999999999.00"


# ---------------------------------------------------------------------------
# Field — digits propagation
# ---------------------------------------------------------------------------

def test_field_overflow_on_assignment():
    class R(Record):
        amount = Field(places=2, digits=3)

    r = R()
    with pytest.raises(FieldOverflowError):
        r.amount = "1000.00"   # 4 integer digits


def test_field_overflow_via_init():
    class R(Record):
        amount = Field(places=2, digits=3)

    with pytest.raises(FieldOverflowError):
        R(amount="9999.99")


def test_field_within_digits_capacity():
    class R(Record):
        amount = Field(places=2, digits=3)

    r = R(amount="999.99")
    assert str(r.amount) == "999.99"


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

def test_public_api_exports():
    import fixfield
    expected = {
        "__version__",
        "RoundingStrategy",
        "FixedDecimal",
        "FieldOverflowError",
        "Field",
        "FieldValue",
        "Record",
    }
    assert expected.issubset(set(fixfield.__all__))
    for name in expected:
        assert hasattr(fixfield, name)


def test_version_is_string():
    import fixfield
    assert isinstance(fixfield.__version__, str)
    assert fixfield.__version__ == "0.1.0"


# ---------------------------------------------------------------------------
# Reverse arithmetic operators
# ---------------------------------------------------------------------------

def test_radd():
    fd = FixedDecimal("1.50", places=2)
    result = 2 + fd
    assert str(result) == "3.50"
    assert result.places == 2


def test_rsub():
    fd = FixedDecimal("1.50", places=2)
    result = 5 - fd
    assert str(result) == "3.50"


def test_rmul():
    fd = FixedDecimal("1.50", places=2)
    result = 3 * fd
    assert str(result) == "4.50"


def test_rtruediv():
    fd = FixedDecimal("2.00", places=2)
    result = 10 / fd
    assert str(result) == "5.00"


def test_reverse_ops_inherit_self_precision():
    fd = FixedDecimal("1.00", places=4, rounding=RoundingStrategy.ROUND_FLOOR)
    result = 2 * fd
    assert result.places == 4
    assert result.rounding == RoundingStrategy.ROUND_FLOOR


# ---------------------------------------------------------------------------
# copy / replace
# ---------------------------------------------------------------------------

def test_copy_returns_equal_value():
    fd = FixedDecimal("1.50", places=2)
    c = fd.copy()
    assert c == fd
    assert c is not fd


def test_copy_preserves_all_attrs():
    fd = FixedDecimal("1.50", places=4, rounding=RoundingStrategy.ROUND_FLOOR, digits=3)
    c = fd.copy()
    assert c.places   == fd.places
    assert c.rounding == fd.rounding
    assert c.digits   == fd.digits


def test_replace_places():
    fd = FixedDecimal("1.505", places=3)
    result = fd.replace(places=2)
    assert result.places == 2
    assert str(result) == "1.51"   # re-rounded to 2 places


def test_replace_rounding():
    fd = FixedDecimal("1.505", places=2, rounding=RoundingStrategy.ROUND_HALF_UP)
    result = fd.replace(rounding=RoundingStrategy.ROUND_FLOOR)
    assert result.rounding == RoundingStrategy.ROUND_FLOOR


def test_replace_removes_digits_cap():
    fd = FixedDecimal("99.99", places=2, digits=2)
    result = fd.replace(digits=None)
    assert result.digits is None
    assert str(FixedDecimal("999.99", places=2, digits=result.digits)) == "999.99"


def test_replace_original_unchanged():
    fd = FixedDecimal("1.50", places=2)
    fd.replace(places=4)
    assert fd.places == 2   # original not mutated
