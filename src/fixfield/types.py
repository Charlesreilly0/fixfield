

from __future__ import annotations
import decimal
from fixfield.rounding import RoundingStrategy, apply

type _NUMBER = str | float | int | decimal.Decimal


class FieldOverflowError(ValueError):
    """Raised when a value exceeds the declared integer-digit capacity."""


def _to_decimal(value: _NUMBER) -> decimal.Decimal:
    if isinstance(value, float):
        return decimal.Decimal(str(value))
    return decimal.Decimal(value)  # type: ignore[arg-type]


class FixedDecimal:
    places: int
    digits: int | None
    rounding: RoundingStrategy

    def __init__(
        self,
        value: _NUMBER,
        places: int = 2,
        rounding: RoundingStrategy = RoundingStrategy.ROUND_HALF_UP,
        digits: int | None = None,
    ) -> None:
        self.places = places
        self.rounding = rounding
        self.digits = digits
        rounded = apply(_to_decimal(value), places, rounding)
        if digits is not None:
            limit = decimal.Decimal(10) ** digits
            if abs(rounded) >= limit:
                raise FieldOverflowError(
                    f"value {rounded} exceeds {digits} integer digits"
                )
        self.value = rounded

    def _new(self, value: decimal.Decimal) -> FixedDecimal:
        return FixedDecimal(value, self.places, self.rounding, self.digits)

    def _coerce(self, other: FixedDecimal | _NUMBER) -> FixedDecimal:
        if not isinstance(other, FixedDecimal):
            return FixedDecimal(other, self.places, self.rounding, self.digits)
        return other

    # Arithmetic --------------------------------------------------------------
    # Convention: the LEFT operand's precision (places, rounding, digits)
    # always governs the result. The right operand's rounding is ignored.
    # This mirrors COBOL's COMPUTE statement where the receiving field
    # defines the result's precision.

    def __add__(self, other: FixedDecimal | _NUMBER) -> FixedDecimal:
        return self._new(self.value + self._coerce(other).value)

    def __sub__(self, other: FixedDecimal | _NUMBER) -> FixedDecimal:
        return self._new(self.value - self._coerce(other).value)

    def __mul__(self, other: FixedDecimal | _NUMBER) -> FixedDecimal:
        return self._new(self.value * self._coerce(other).value)

    def __truediv__(self, other: FixedDecimal | _NUMBER) -> FixedDecimal:
        return self._new(self.value / self._coerce(other).value)

    # Reverse arithmetic — scalars on the left (e.g. 2 * price) ---------------
    # Left operand's precision is unknown so we use self's precision.

    def __radd__(self, other: _NUMBER) -> FixedDecimal:
        return self._new(_to_decimal(other) + self.value)

    def __rsub__(self, other: _NUMBER) -> FixedDecimal:
        return self._new(_to_decimal(other) - self.value)

    def __rmul__(self, other: _NUMBER) -> FixedDecimal:
        return self._new(_to_decimal(other) * self.value)

    def __rtruediv__(self, other: _NUMBER) -> FixedDecimal:
        return self._new(_to_decimal(other) / self.value)

    def __neg__(self) -> FixedDecimal:
        return self._new(-self.value)

    def __abs__(self) -> FixedDecimal:
        return self._new(abs(self.value))

    # Copy / replace ----------------------------------------------------------

    def copy(self) -> FixedDecimal:
        """Return an identical copy."""
        return self._new(self.value)

    def replace(
        self,
        *,
        places: int | None = None,
        rounding: RoundingStrategy | None = None,
        digits: int | None = ...,  # type: ignore[assignment]
    ) -> FixedDecimal:
        """
        Return a new ``FixedDecimal`` with selected attributes changed.
        The value is re-rounded to the new precision.

        Pass ``digits=None`` explicitly to remove the digit cap.
        """
        new_places   = self.places   if places   is None else places
        new_rounding = self.rounding if rounding is None else rounding
        new_digits   = self.digits   if digits   is ... else digits
        return FixedDecimal(self.value, new_places, new_rounding, new_digits)

    # Comparisons -------------------------------------------------------------
    # FixedDecimal vs FixedDecimal: precision-sensitive (value AND places must match).
    # FixedDecimal vs raw scalar: value-only, so FixedDecimal("1.00", places=2) == 1
    # is True regardless of places. This is intentional — raw scalars carry no
    # precision information.

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FixedDecimal):
            return self.value == other.value and self.places == other.places
        if isinstance(other, (str, int, float, decimal.Decimal)):
            return self.value == _to_decimal(other)
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other: FixedDecimal | _NUMBER) -> bool:
        return self.value < self._coerce(other).value

    def __le__(self, other: FixedDecimal | _NUMBER) -> bool:
        return self.value <= self._coerce(other).value

    def __gt__(self, other: FixedDecimal | _NUMBER) -> bool:
        return self.value > self._coerce(other).value

    def __ge__(self, other: FixedDecimal | _NUMBER) -> bool:
        return self.value >= self._coerce(other).value

    def __hash__(self) -> int:
        # Includes places so precision-different instances with equal values
        # hash differently — consistent with precision-sensitive __eq__.
        return hash((self.value, self.places))

    # Representation ----------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"FixedDecimal(value={self.value}, places={self.places}, "
            f"rounding={self.rounding})"
        )

    def __str__(self) -> str:
        return f"{self.value:.{self.places}f}"