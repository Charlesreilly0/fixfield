import decimal
import pytest
from fixfield.rounding import RoundingStrategy, apply


@pytest.mark.parametrize("value, places, strategy, expected", [
    # ROUND_HALF_UP — halves go away from zero
    ("2.5",  0, RoundingStrategy.ROUND_HALF_UP,   "3"),
    ("3.5",  0, RoundingStrategy.ROUND_HALF_UP,   "4"),
    ("-2.5", 0, RoundingStrategy.ROUND_HALF_UP,   "-3"),
    ("2.55", 1, RoundingStrategy.ROUND_HALF_UP,   "2.6"),
    ("2.45", 1, RoundingStrategy.ROUND_HALF_UP,   "2.5"),

    # ROUND_HALF_DOWN — halves go toward zero
    ("2.5",  0, RoundingStrategy.ROUND_HALF_DOWN, "2"),
    ("3.5",  0, RoundingStrategy.ROUND_HALF_DOWN, "3"),
    ("-2.5", 0, RoundingStrategy.ROUND_HALF_DOWN, "-2"),

    # ROUND_HALF_EVEN — halves round to nearest even digit (banker's rounding)
    ("2.5",  0, RoundingStrategy.ROUND_HALF_EVEN, "2"),
    ("3.5",  0, RoundingStrategy.ROUND_HALF_EVEN, "4"),
    ("4.5",  0, RoundingStrategy.ROUND_HALF_EVEN, "4"),
    ("5.5",  0, RoundingStrategy.ROUND_HALF_EVEN, "6"),

    # ROUND_HALF_ODD — halves round to nearest odd digit
    ("2.5",  0, RoundingStrategy.ROUND_HALF_ODD,  "3"),
    ("3.5",  0, RoundingStrategy.ROUND_HALF_ODD,  "3"),
    ("4.5",  0, RoundingStrategy.ROUND_HALF_ODD,  "5"),
    ("5.5",  0, RoundingStrategy.ROUND_HALF_ODD,  "5"),

    # ROUND_UP — away from zero regardless
    ("2.1",  0, RoundingStrategy.ROUND_UP,        "3"),
    ("-2.1", 0, RoundingStrategy.ROUND_UP,        "-3"),
    ("2.0",  0, RoundingStrategy.ROUND_UP,        "2"),   # exact — no change

    # ROUND_DOWN — toward zero regardless (truncate)
    ("2.9",  0, RoundingStrategy.ROUND_DOWN,      "2"),
    ("-2.9", 0, RoundingStrategy.ROUND_DOWN,      "-2"),
    ("2.0",  0, RoundingStrategy.ROUND_DOWN,      "2"),   # exact — no change

    # ROUND_CEILING — toward positive infinity
    ("2.1",  0, RoundingStrategy.ROUND_CEILING,   "3"),
    ("-2.9", 0, RoundingStrategy.ROUND_CEILING,   "-2"),

    # ROUND_FLOOR — toward negative infinity
    ("2.9",  0, RoundingStrategy.ROUND_FLOOR,     "2"),
    ("-2.1", 0, RoundingStrategy.ROUND_FLOOR,     "-3"),

    # Decimal places > 0
    ("1.005", 2, RoundingStrategy.ROUND_HALF_UP,  "1.01"),
    ("1.004", 2, RoundingStrategy.ROUND_HALF_UP,  "1.00"),
    ("1.999", 2, RoundingStrategy.ROUND_HALF_UP,  "2.00"),
])
def test_apply(value, places, strategy, expected):
    result = apply(decimal.Decimal(value), places, strategy)
    assert result == decimal.Decimal(expected)
