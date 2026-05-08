"""Tests for ExternalField[T] — the pass-through descriptor."""
from __future__ import annotations

import uuid
from enum import Enum

import pytest

from fixfield import (
    CurrencyField,
    ExternalField,
    Field,
    Record,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class Color(Enum):
    RED = "red"
    BLUE = "blue"


class Order(Record):
    order_id  = ExternalField(uuid.UUID, default_factory=uuid.uuid4)
    reference = ExternalField(str, default="")
    total     = CurrencyField()


class Tagged(Record):
    tag   = ExternalField(str, default="none")
    color = ExternalField(Color, default=Color.RED)
    value = Field(places=2)


class JsonOrder(Record):
    order_id  = ExternalField(
        uuid.UUID,
        default_factory=uuid.uuid4,
        json_encoder=str,
        json_decoder=uuid.UUID,
    )
    reference = ExternalField(str, default="")
    total     = CurrencyField()


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_default_factory_generates_uuid(self):
        o = Order(reference="X", total="10.00")
        assert isinstance(o.order_id, uuid.UUID)

    def test_default_factory_unique_per_instance(self):
        a = Order(reference="A", total="1.00")
        b = Order(reference="B", total="2.00")
        assert a.order_id != b.order_id

    def test_static_default(self):
        t = Tagged(value="5.00")
        assert t.tag == "none"
        assert t.color == Color.RED

    def test_explicit_value_overrides_factory(self):
        uid = uuid.uuid4()
        o = Order(order_id=uid, reference="Y", total="0.00")
        assert o.order_id == uid

    def test_both_default_and_factory_raises(self):
        with pytest.raises(ValueError, match="not both"):
            ExternalField(str, default="x", default_factory=lambda: "y")


# ---------------------------------------------------------------------------
# __set__ type checking
# ---------------------------------------------------------------------------

class TestTypeChecking:
    def test_wrong_type_raises(self):
        o = Order(reference="A", total="1.00")
        with pytest.raises(TypeError, match="ExternalField 'order_id' expects UUID"):
            o.order_id = "not-a-uuid"  # type: ignore[assignment]

    def test_correct_type_accepted(self):
        uid = uuid.uuid4()
        o = Order(reference="A", total="1.00")
        o.order_id = uid
        assert o.order_id == uid

    def test_none_allowed_regardless_of_type(self):
        o = Order(reference="A", total="1.00")
        o.order_id = None  # type: ignore[assignment]
        assert o.order_id is None

    def test_bare_object_type_skips_check(self):
        class Loose(Record):
            data = ExternalField()  # field_type defaults to object
            price = Field(places=2)

        r = Loose(data=42, price="1.00")
        assert r.data == 42
        r.data = "hello"
        assert r.data == "hello"


# ---------------------------------------------------------------------------
# Class-level access returns the descriptor
# ---------------------------------------------------------------------------

class TestClassAccess:
    def test_class_access_returns_descriptor(self):
        desc = Order.order_id  # type: ignore[attr-defined]
        assert isinstance(desc, ExternalField)

    def test_repr_of_descriptor(self):
        assert repr(Order.order_id) == "ExternalField(UUID)"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# width raises TypeError
# ---------------------------------------------------------------------------

class TestWidth:
    def test_width_raises(self):
        with pytest.raises(TypeError, match="does not support fixed-width"):
            _ = Order.order_id.width  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Record integration: __repr__, __eq__, to_dict
# ---------------------------------------------------------------------------

class TestRecordIntegration:
    def test_repr_includes_external_field(self):
        uid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        o = Order(order_id=uid, reference="R1", total="9.99")
        r = repr(o)
        assert "order_id" in r
        assert "12345678" in r

    def test_eq_considers_external_field(self):
        uid = uuid.uuid4()
        a = Order(order_id=uid, reference="X", total="1.00")
        b = Order(order_id=uid, reference="X", total="1.00")
        assert a == b

    def test_eq_differs_on_external_field(self):
        a = Order(order_id=uuid.uuid4(), reference="X", total="1.00")
        b = Order(order_id=uuid.uuid4(), reference="X", total="1.00")
        assert a != b

    def test_to_dict_includes_external_field(self):
        uid = uuid.uuid4()
        o = Order(order_id=uid, reference="R", total="5.00")
        d = o.to_dict()
        assert d["order_id"] == uid
        assert d["reference"] == "R"

    def test_enum_round_trip_in_dict(self):
        t = Tagged(tag="hello", color=Color.BLUE, value="3.14")
        d = t.to_dict()
        assert d["color"] == Color.BLUE


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

class TestJson:
    def test_to_json_encodes_uuid_as_str(self):
        import json
        uid = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        o = JsonOrder(order_id=uid, reference="J1", total="12.34")
        parsed = json.loads(o.to_json())
        assert parsed["order_id"] == str(uid)
        assert parsed["reference"] == "J1"
        assert parsed["total"] == "12.34"

    def test_from_json_decodes_uuid(self):
        import json
        uid = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        payload = json.dumps({
            "order_id": str(uid),
            "reference": "J2",
            "total": "7.77",
        })
        o = JsonOrder.from_json(payload)
        assert o.order_id == uid
        assert isinstance(o.order_id, uuid.UUID)

    def test_from_json_round_trip(self):
        uid = uuid.uuid4()
        original = JsonOrder(order_id=uid, reference="RT", total="99.99")
        restored = JsonOrder.from_json(original.to_json())
        assert restored.order_id == original.order_id
        assert restored.reference == original.reference
        assert restored.total == original.total


# ---------------------------------------------------------------------------
# serializable=True blocks ExternalField
# ---------------------------------------------------------------------------

class TestSerializableBlock:
    def test_serializable_with_external_field_raises(self):
        with pytest.raises(TypeError, match="ExternalField"):
            class Bad(Record, serializable=True):
                uid   = ExternalField(uuid.UUID, default_factory=uuid.uuid4)
                price = Field(places=2)
