from __future__ import annotations

from typing import Generic, Self, TypeVar, overload
from fixfield.field import Field, FieldValue
from fixfield.types import FixedDecimal

_R = TypeVar("_R", bound="Record")


class RecordField(Generic[_R]):
    """
    Descriptor for embedding a nested Record as a field within another Record.

    Example::

        class Address(Record):
            zip_code = Field(places=0, digits=5)

        class Customer(Record):
            customer_id = Field(places=0, digits=6)
            address     = RecordField(Address)
    """

    def __init__(self, record_type: type[_R]) -> None:
        self.record_type = record_type
        self._attr: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr = f"_recordfield_{name}"

    @overload
    def __get__(self, obj: None, objtype: type) -> RecordField[_R]: ...
    @overload
    def __get__(self, obj: object, objtype: type) -> _R: ...

    def __get__(self, obj: object | None, objtype: type) -> RecordField[_R] | _R:
        if obj is None:
            return self
        value = obj.__dict__.get(self._attr)
        if value is None:
            return self.record_type()
        return value  # type: ignore[return-value]

    def __set__(self, obj: object, value: _R) -> None:
        if not isinstance(value, self.record_type):
            raise TypeError(
                f"Expected {self.record_type.__name__}, got {type(value).__name__}"
            )
        obj.__dict__[self._attr] = value

    @property
    def width(self) -> int:
        """Total fixed-width character length of the nested record."""
        return sum(attr.width for attr in self.record_type._all_attrs.values())

    def __repr__(self) -> str:
        return f"RecordField({self.record_type.__name__})"


class Record:
    """
    Base class for structured groups of Fields.

    Subclass and declare Fields (and optionally RecordFields) as class
    attributes. Record generates an __init__ that accepts values for each
    declared attribute by keyword, coercing each through its declared
    precision automatically.

    Arithmetic convention: the LEFT operand's precision governs the result.

    Example::

        class Invoice(Record):
            price    = Field(places=2)
            tax_rate = Field(places=4)
            total    = Field(places=2)

        inv = Invoice(price="19.99", tax_rate="0.0825", total="0")
        inv.total = inv.price * inv.tax_rate + inv.price
    """

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Collect all declared fields in declaration order
        all_attrs: dict[str, Field | RecordField] = {
            name: obj
            for name, obj in cls.__dict__.items()
            if isinstance(obj, (Field, RecordField))
        }
        cls._all_attrs: dict[str, Field | RecordField] = all_attrs
        cls._fields: dict[str, Field] = {
            n: o for n, o in all_attrs.items() if isinstance(o, Field)
        }
        cls._record_fields: dict[str, RecordField] = {
            n: o for n, o in all_attrs.items() if isinstance(o, RecordField)
        }
        cls.__init__ = _make_init(all_attrs)  # type: ignore[method-assign]

    def __repr__(self) -> str:
        parts = ", ".join(
            f"{name}={getattr(self, name)!s}"
            for name in self._all_attrs
        )
        return f"{type(self).__name__}({parts})"

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return all(
            getattr(self, name) == getattr(other, name)
            for name in self._all_attrs
        )

    def to_dict(self) -> dict[str, FixedDecimal | Record]:
        return {name: getattr(self, name) for name in self._all_attrs}

    def to_string(self) -> str:
        """
        Serialise the record to a fixed-width string.
        Every Field must have ``digits`` set. RecordFields recurse into
        their nested record's ``to_string``.
        """
        parts: list[str] = []
        for name, attr in self._all_attrs.items():
            value = getattr(self, name)
            if isinstance(attr, RecordField):
                parts.append(value.to_string())
            else:
                parts.append(str(value).rjust(attr.width))
        return "".join(parts)

    @classmethod
    def from_string(cls, text: str) -> Self:
        """
        Parse a fixed-width string produced by ``to_string``.
        Raises ``ValueError`` if ``text`` is shorter than the expected width.
        """
        expected = sum(attr.width for attr in cls._all_attrs.values())
        if len(text) < expected:
            raise ValueError(
                f"{cls.__name__}.from_string expects at least {expected} "
                f"characters, got {len(text)}"
            )
        offset = 0
        kwargs: dict[str, str | Record] = {}
        for name, attr in cls._all_attrs.items():
            w = attr.width
            chunk = text[offset : offset + w]
            if isinstance(attr, RecordField):
                kwargs[name] = attr.record_type.from_string(chunk)
            else:
                kwargs[name] = chunk.strip()
            offset += w
        return cls(**kwargs)


def _make_init(all_attrs: dict[str, Field | RecordField]):
    """Generates a keyword-only __init__ for all declared attrs."""
    attr_names = list(all_attrs.keys())

    def __init__(self: Record, **kwargs: FieldValue | Record) -> None:
        for name in attr_names:
            value = kwargs.get(name)
            attr = all_attrs[name]
            if value is not None:
                setattr(self, name, value)
            elif isinstance(attr, Field) and attr.default is not None:
                object.__setattr__(self, f"_field_{name}", attr.default)
            # else: leave unset — descriptor returns zero/empty on access

    __init__.__doc__ = (
        "Args:\n" + "\n".join(f"    {n}: {all_attrs[n]}" for n in attr_names)
    )

    return __init__
