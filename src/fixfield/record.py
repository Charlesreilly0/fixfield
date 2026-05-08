from __future__ import annotations

import json
from typing import Generic, Self, TypeVar, overload
from fixfield.field import Field, FieldValue, ExternalField
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

    def __init_subclass__(cls, serializable: bool = False, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Collect all declared fields in declaration order
        all_attrs: dict[str, Field | RecordField | ExternalField] = {
            name: obj
            for name, obj in cls.__dict__.items()
            if isinstance(obj, (Field, RecordField, ExternalField))
        }
        cls._all_attrs: dict[str, Field | RecordField | ExternalField] = all_attrs
        cls._fields: dict[str, Field] = {
            n: o for n, o in all_attrs.items() if isinstance(o, Field)
        }
        cls._record_fields: dict[str, RecordField] = {
            n: o for n, o in all_attrs.items() if isinstance(o, RecordField)
        }
        cls._external_fields: dict[str, ExternalField] = {
            n: o for n, o in all_attrs.items() if isinstance(o, ExternalField)
        }
        cls.__init__ = _make_init(all_attrs)  # type: ignore[method-assign]

        if serializable:
            # ExternalFields always block fixed-width serialisation
            raw_names = list(cls._external_fields.keys())
            if raw_names:
                raise TypeError(
                    f"{cls.__name__} declared serializable=True but contains "
                    f"ExternalFields which do not support fixed-width serialisation: "
                    f"{', '.join(raw_names)}"
                )
            missing = [
                name for name, attr in all_attrs.items()
                if isinstance(attr, Field) and attr.digits is None
            ]
            if missing:
                raise TypeError(
                    f"{cls.__name__} declared serializable=True but the following "
                    f"Fields are missing 'digits': {', '.join(missing)}"
                )

    def __repr__(self) -> str:
        parts = ", ".join(
            f"{name}={getattr(self, name)!r}"
            if isinstance(self._all_attrs[name], ExternalField)
            else f"{name}={getattr(self, name)!s}"
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

    def to_json(self) -> str:
        """
        Serialise the record to a JSON string.
        ``FixedDecimal`` values are serialised as their canonical string
        representation (e.g. ``"19.99"``). Nested ``RecordField`` values
        are serialised as nested objects.

        Example::

            inv.to_json()
            # '{"price": "19.99", "tax_rate": "0.0825", "total": "21.64"}'
        """
        def _to_jsonable(name: str, value: object, attrs: dict) -> object:
            if isinstance(value, Record):
                return {k: _to_jsonable(k, v, value._all_attrs)
                        for k, v in value.to_dict().items()}
            attr = attrs[name]
            if isinstance(attr, ExternalField) and callable(attr.json_encoder):
                return attr.json_encoder(value)
            return str(value)  # FixedDecimal.__str__ gives canonical form

        return json.dumps({name: _to_jsonable(name, getattr(self, name), self._all_attrs)
                           for name in self._all_attrs})

    @classmethod
    def from_json(cls, text: str) -> Self:
        """
        Parse a JSON string produced by :meth:`to_json`.
        Raises ``ValueError`` if a required field is missing from the JSON.

        Example::

            Invoice.from_json('{"price": "19.99", "tax_rate": "0.0825"}')
        """
        data: dict[str, object] = json.loads(text)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, object]) -> Self:
        kwargs: dict[str, object] = {}
        for name, attr in cls._all_attrs.items():
            if name not in data:
                continue
            value = data[name]
            if isinstance(attr, RecordField):
                if not isinstance(value, dict):
                    raise ValueError(
                        f"Expected a JSON object for nested field '{name}', "
                        f"got {type(value).__name__}"
                    )
                kwargs[name] = attr.record_type._from_dict(value)
            elif isinstance(attr, ExternalField):
                # Apply json_decoder if provided, otherwise store raw JSON value
                if callable(attr.json_decoder):
                    kwargs[name] = attr.json_decoder(value)
                else:
                    kwargs[name] = value
            else:
                kwargs[name] = value  # Field.__set__ will coerce the string
        return cls(**kwargs)  # type: ignore[arg-type]

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


def _make_init(all_attrs: dict[str, Field | RecordField | ExternalField]):
    """Generates a keyword-only __init__ for all declared attrs."""
    attr_names = list(all_attrs.keys())

    def __init__(self: Record, **kwargs: FieldValue | Record | object) -> None:
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
