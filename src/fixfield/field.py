from __future__ import annotations

from typing import overload
from fixfield.rounding import RoundingStrategy
from fixfield.types import FixedDecimal, _NUMBER

type FieldValue = _NUMBER | FixedDecimal


class Field:
    def __init__(
        self,
        places: int = 2,
        rounding: RoundingStrategy = RoundingStrategy.ROUND_HALF_UP,
        default: _NUMBER | None = None,
        digits: int | None = None,
    ) -> None:
        self.places = places
        self.rounding = rounding
        self.digits = digits
        self.default = (
            FixedDecimal(default, places, rounding, digits)
            if default is not None
            else None
        )
        self._attr: str = ""  # set by __set_name__

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr = f"_field_{name}"

    @overload
    def __get__(self, obj: None, objtype: type) -> Field: ...

    @overload
    def __get__(self, obj: object, objtype: type) -> FixedDecimal: ...

    def __get__(self, obj: object | None, objtype: type) -> Field | FixedDecimal:
        if obj is None:
            return self
        value = obj.__dict__.get(self._attr)
        if value is None:
            if self.default is not None:
                return self.default
            return FixedDecimal(0, self.places, self.rounding, self.digits)
        return value

    def __set__(self, obj: object, value: FieldValue) -> None:
        raw = value.value if isinstance(value, FixedDecimal) else value
        obj.__dict__[self._attr] = FixedDecimal(
            raw, self.places, self.rounding, self.digits
        )

    @property
    def width(self) -> int:
        """
        Fixed-width character length for this field.
        Requires ``digits`` to be set.

        Format: [sign(1)] + [integer digits] + [. + decimal places if places > 0]
        Example: digits=5, places=2  →  "-99999.99"  → width 9
        """
        if self.digits is None:
            raise ValueError(
                "Field must have 'digits' set to use fixed-width serialization"
            )
        decimal_part = 1 + self.places if self.places > 0 else 0
        return 1 + self.digits + decimal_part   # 1 for sign

    def __repr__(self) -> str:
        return (
            f"Field(places={self.places}, rounding={self.rounding}, "
            f"digits={self.digits}, default={self.default})"
        )
