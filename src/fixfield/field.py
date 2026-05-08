from __future__ import annotations

from typing import Callable, Generic, TypeVar, overload
from fixfield.rounding import RoundingStrategy
from fixfield.types import FixedDecimal, FieldOverflowError, _NUMBER

type FieldValue = _NUMBER | FixedDecimal

_T = TypeVar("_T")
_MISSING = object()  # sentinel for "field has never been set"


class Field:
    def __init__(
        self,
        places: int = 2,
        rounding: RoundingStrategy = RoundingStrategy.ROUND_HALF_UP,
        default: _NUMBER | None = None,
        digits: int | None = None,
        signed: bool = True,
    ) -> None:
        self.places = places
        self.rounding = rounding
        self.digits = digits
        self.signed = signed
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
        coerced = FixedDecimal(raw, self.places, self.rounding, self.digits)
        if not self.signed and coerced.value < 0:
            raise FieldOverflowError(
                f"Field '{self._attr.removeprefix('_field_')}' is unsigned "
                f"but received negative value {coerced}"
            )
        obj.__dict__[self._attr] = coerced

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
            f"digits={self.digits}, default={self.default}, signed={self.signed})"
        )


# ---------------------------------------------------------------------------
# ExternalField — pass-through descriptor for non-decimal values
# ---------------------------------------------------------------------------

class ExternalField(Generic[_T]):
    """
    A pass-through descriptor for storing any Python value inside a
    :class:`Record` without fixed-decimal coercion.

    Use this when a record needs to carry non-numeric data — UUIDs, strings,
    enums, plain ints, etc. — alongside its :class:`Field` declarations.

    ``ExternalField`` participates in the generated ``__init__``, ``__repr__``,
    ``__eq__``, ``to_dict()``, and ``to_json()`` / ``from_json()``.

    It does **not** support fixed-width serialisation (``to_string`` /
    ``from_string``). Calling those methods on a ``Record`` that contains an
    ``ExternalField`` raises ``TypeError``.

    Parameters
    ----------
    field_type:
        The Python type to store. Used for type-checking on assignment and
        as the default ``json_decoder``.
    default:
        Static default value returned when the field has not been set.
        Mutually exclusive with ``default_factory``.
    default_factory:
        Zero-argument callable invoked once per instance to produce a default
        value. Use this for mutable defaults (e.g. ``uuid.uuid4``).
    json_encoder:
        Callable used by ``to_json()`` to serialise the value.
        Defaults to ``str``.
    json_decoder:
        Callable used by ``from_json()`` to deserialise the stored JSON value
        back to the original type. Defaults to ``field_type`` when provided,
        or ``None`` (identity / raw JSON string) otherwise.

    Example::

        import uuid
        from fixfield import Record, Field, ExternalField, CurrencyField

        class Order(Record):
            order_id  = ExternalField(uuid.UUID, default_factory=uuid.uuid4)
            reference = ExternalField(str, default="")
            total     = CurrencyField()

        o = Order(reference="ORD-001", total="99.99")
        print(o.order_id)    # UUID('...')
        print(o.to_json())
        # '{"order_id": "...", "reference": "ORD-001", "total": "99.99"}'
    """

    def __init__(
        self,
        field_type: type[_T] = object,  # type: ignore[assignment]
        *,
        default: _T | None = None,
        default_factory: Callable[[], _T] | None = None,
        json_encoder: Callable[[_T], object] | None = None,
        json_decoder: Callable[..., _T] | None = None,
    ) -> None:
        if default is not None and default_factory is not None:
            raise ValueError(
                "Specify either 'default' or 'default_factory', not both"
            )
        self.field_type = field_type
        self._default = default
        self.default_factory = default_factory
        # Default encoder: str(); default decoder: field_type if not bare object
        self.json_encoder: Callable[[_T], object] = json_encoder or str
        self.json_decoder: Callable[[object], _T] | None = (
            json_decoder
            if json_decoder is not None
            else (field_type if field_type is not object else None)  # type: ignore[return-value]
        )
        self._attr: str = ""   # set by __set_name__
        self._name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr = f"_external_{name}"
        self._name = name

    @overload
    def __get__(self, obj: None, objtype: type) -> ExternalField[_T]: ...
    @overload
    def __get__(self, obj: object, objtype: type) -> _T: ...

    def __get__(self, obj: object | None, objtype: type) -> ExternalField[_T] | _T:
        if obj is None:
            return self
        value = obj.__dict__.get(self._attr, _MISSING)
        if value is _MISSING:
            if self._default is not None:
                return self._default
            if self.default_factory is not None:
                # Generate once and cache on the instance
                generated = self.default_factory()
                obj.__dict__[self._attr] = generated
                return generated
            return None  # type: ignore[return-value]
        return value  # type: ignore[return-value]

    def __set__(self, obj: object, value: object) -> None:
        if (
            self.field_type is not object
            and value is not None
            and not isinstance(value, self.field_type)
        ):
            raise TypeError(
                f"ExternalField '{self._name}' expects "
                f"{self.field_type.__name__}, got {type(value).__name__}"
            )
        obj.__dict__[self._attr] = value

    @property
    def default(self) -> _T | None:
        return self._default

    @property
    def width(self) -> int:
        raise TypeError(
            f"ExternalField '{self._name}' does not support fixed-width "
            "serialisation. Use to_json() / from_json() instead, or replace "
            "with a Field."
        )

    def __repr__(self) -> str:
        return f"ExternalField({self.field_type.__name__})"


# ---------------------------------------------------------------------------
# FieldTemplate — reusable, pre-configured Field prototype
# ---------------------------------------------------------------------------

class FieldTemplate:
    """
    A reusable :class:`Field` prototype with pre-configured defaults.

    Call a ``FieldTemplate`` instance to produce a ``Field``, optionally
    overriding individual parameters at the call site.

    This is the recommended way to define project-wide or domain-specific
    field types without repeating configuration everywhere.

    Example::

        # Define once — in a shared ``fields.py`` or similar
        MoneyField   = FieldTemplate(places=2, digits=8, signed=False)
        QuantityField = FieldTemplate(places=0, digits=6, signed=False)

        # Use in any Record
        class Invoice(Record):
            price    = MoneyField()              # defaults
            discount = MoneyField(signed=True)   # allow negatives on this field
            qty      = QuantityField()

    All keyword arguments accepted by :class:`Field` are valid here.
    """

    def __init__(
        self,
        places: int = 2,
        rounding: RoundingStrategy = RoundingStrategy.ROUND_HALF_UP,
        default: _NUMBER | None = None,
        digits: int | None = None,
        signed: bool = True,
    ) -> None:
        self._defaults: dict[str, object] = {
            "places":   places,
            "rounding": rounding,
            "default":  default,
            "digits":   digits,
            "signed":   signed,
        }

    def __call__(
        self,
        *,
        places: int | None = None,
        rounding: RoundingStrategy | None = None,
        default: _NUMBER | None = ...,  # type: ignore[assignment]
        digits: int | None = ...,       # type: ignore[assignment]
        signed: bool | None = None,
    ) -> Field:
        """
        Return a new :class:`Field` using the template's defaults, with any
        supplied keyword arguments overriding those defaults.
        """
        resolved: dict[str, object] = dict(self._defaults)
        if places   is not None:
            resolved["places"]   = places
        if rounding is not None:
            resolved["rounding"] = rounding
        if default  is not ...:
            resolved["default"]  = default
        if digits   is not ...:
            resolved["digits"]   = digits
        if signed   is not None:
            resolved["signed"]   = signed
        return Field(**resolved)  # type: ignore[arg-type]

    def __repr__(self) -> str:
        parts = ", ".join(f"{k}={v!r}" for k, v in self._defaults.items())
        return f"FieldTemplate({parts})"


# ---------------------------------------------------------------------------
# Convenience field factories (built on FieldTemplate)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Built-in FieldTemplate instances
# ---------------------------------------------------------------------------
# Each is a FieldTemplate, so call-site overrides work:
#   price = CurrencyField(digits=6)        # override digits
#   rate  = PercentField(signed=False)     # override signed

CurrencyField = FieldTemplate(places=2, digits=8, signed=True)
"""
:class:`FieldTemplate` for currency values (2 decimal places, 8 integer digits).

Maximum value: ±99,999,999.99. Override any parameter at the call site::

    class Invoice(Record):
        price    = CurrencyField()           # ±99,999,999.99
        subtotal = CurrencyField(digits=6)   # ±999,999.99
        fee      = CurrencyField(signed=False)  # unsigned
"""

PercentField = FieldTemplate(places=4, digits=3, signed=True)
"""
:class:`FieldTemplate` for percentage/rate values (4 decimal places, 3 integer digits).

Maximum value: ±999.9999. Override any parameter at the call site::

    class TaxRecord(Record):
        rate = PercentField()            # e.g. 0.0825
        cap  = PercentField(digits=2)    # max ±99.9999
"""

QuantityField = FieldTemplate(places=0, digits=6, signed=False)
"""
:class:`FieldTemplate` for whole-number quantities (0 decimal places, unsigned).

Maximum value: 999,999. Override any parameter at the call site::

    class OrderLine(Record):
        qty        = QuantityField()           # max 999,999
        large_qty  = QuantityField(digits=9)   # max 999,999,999
"""

RateField = FieldTemplate(places=6, digits=2, signed=False)
"""
:class:`FieldTemplate` for exchange rates / unit rates (6 decimal places, unsigned).

Maximum value: 99.999999. Override any parameter at the call site::

    class FXRate(Record):
        usd_gbp = RateField()           # e.g. 1.234567
        exotic  = RateField(digits=4)   # e.g. 9999.999999
"""

AccountNumberField = FieldTemplate(places=0, digits=10, signed=False)
"""
:class:`FieldTemplate` for integer account / identifier fields (no decimal, unsigned).

Maximum value: 9,999,999,999. Override any parameter at the call site::

    class Customer(Record):
        account_id = AccountNumberField()
        branch_id  = AccountNumberField(digits=4)
"""
