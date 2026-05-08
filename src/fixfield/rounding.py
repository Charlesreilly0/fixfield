


import decimal
from enum import Enum, auto

class RoundingStrategy(Enum):
    ROUND_HALF_UP   = auto()
    ROUND_HALF_DOWN = auto()
    ROUND_UP        = auto()
    ROUND_DOWN      = auto()
    ROUND_CEILING   = auto()
    ROUND_FLOOR     = auto()
    ROUND_HALF_EVEN = auto()
    ROUND_HALF_ODD  = auto()


def _round_half_odd(value: decimal.Decimal, places: int) -> decimal.Decimal:
    quantizer = decimal.Decimal(10) ** -places
    floor = value.quantize(quantizer, rounding=decimal.ROUND_FLOOR)
    ceil  = value.quantize(quantizer, rounding=decimal.ROUND_CEILING)
    half  = quantizer / 2
    if abs(value - floor) == half:
        # exactly halfway — pick whichever of floor/ceil is odd
        return floor if floor % (2 * quantizer) != 0 else ceil
    # not halfway — normal rounding applies
    return value.quantize(quantizer, rounding=decimal.ROUND_HALF_EVEN)


_DECIMAL_MAP = {
    RoundingStrategy.ROUND_HALF_UP:   decimal.ROUND_HALF_UP,
    RoundingStrategy.ROUND_HALF_DOWN: decimal.ROUND_HALF_DOWN,
    RoundingStrategy.ROUND_UP:        decimal.ROUND_UP,
    RoundingStrategy.ROUND_DOWN:      decimal.ROUND_DOWN,
    RoundingStrategy.ROUND_CEILING:   decimal.ROUND_CEILING,
    RoundingStrategy.ROUND_FLOOR:     decimal.ROUND_FLOOR,
    RoundingStrategy.ROUND_HALF_EVEN: decimal.ROUND_HALF_EVEN,
}


def apply(value: decimal.Decimal, places: int, strategy: RoundingStrategy) -> decimal.Decimal:
    if strategy is RoundingStrategy.ROUND_HALF_ODD:
        return _round_half_odd(value, places)

    with decimal.localcontext() as ctx:
        ctx.rounding = _DECIMAL_MAP[strategy]
        return value.quantize(decimal.Decimal(10) ** -places, context=ctx)
    