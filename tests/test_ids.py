from zoop.utils.ids import generate_id


import pytest


@pytest.mark.unit
def test_same_inputs_same_id():
    assert generate_id("dev-1") == generate_id("dev-1")


@pytest.mark.unit
def test_different_devices_different_ids():
    assert generate_id("dev-1") != generate_id("dev-2")


@pytest.mark.unit
def test_idempotency_key_takes_precedence():
    # When an idempotency key is supplied, identity is derived from it,
    # not from the device id.
    a = generate_id("dev-1", idempotency_key="key-123")
    b = generate_id("dev-2", idempotency_key="key-123")
    assert a == b


@pytest.mark.unit
def test_idempotency_key_differs_from_device_derived():
    assert generate_id("dev-1") != generate_id("dev-1", idempotency_key="key-123")


@pytest.mark.unit
def test_different_idempotency_keys_differ():
    assert generate_id("d", idempotency_key="k1") != generate_id(
        "d", idempotency_key="k2"
    )


@pytest.mark.unit
def test_returns_valid_uuid_string():
    import uuid

    out = generate_id("dev-1")
    # round-trips through uuid.UUID without error
    assert str(uuid.UUID(out)) == out
