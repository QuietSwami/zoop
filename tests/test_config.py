import msgspec
import pytest

from zoop.config import BridgeConfig, Config


@pytest.mark.unit
def test_decode_json_config_into_typed_config():
    raw = b"""
    {
      "bridges": [
        {"type": "mqtt", "id": "main", "options": {"host": "localhost", "port": 1883}},
        {"type": "http", "id": "ingest", "enabled": false}
      ]
    }
    """
    cfg = msgspec.json.decode(raw, type=Config)

    assert isinstance(cfg, Config)
    assert len(cfg.bridges) == 2
    first, second = cfg.bridges
    assert first.type == "mqtt"
    assert first.id == "main"
    assert first.enabled is True  # default
    assert first.options == {"host": "localhost", "port": 1883}
    assert second.enabled is False


@pytest.mark.unit
def test_options_defaults_to_empty_dict():
    cfg = msgspec.json.decode(
        b'{"bridges": [{"type": "mqtt", "id": "x"}]}', type=Config
    )
    assert cfg.bridges[0].options == {}


@pytest.mark.unit
def test_bad_config_missing_required_field_raises():
    # 'id' is required on BridgeConfig.
    with pytest.raises(msgspec.ValidationError):
        msgspec.json.decode(b'{"bridges": [{"type": "mqtt"}]}', type=Config)


@pytest.mark.unit
def test_bad_config_wrong_type_raises():
    with pytest.raises(msgspec.ValidationError):
        msgspec.json.decode(
            b'{"bridges": [{"type": "mqtt", "id": 5}]}', type=Config
        )


@pytest.mark.unit
def test_missing_bridges_raises():
    with pytest.raises(msgspec.ValidationError):
        msgspec.json.decode(b"{}", type=Config)


@pytest.mark.unit
def test_bridgeconfig_is_kw_only():
    cfg = BridgeConfig(type="mqtt", id="x")
    assert cfg.type == "mqtt"
    assert cfg.id == "x"
    assert cfg.enabled is True
