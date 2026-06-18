import uuid

_OBSERVATION_NS = uuid.UUID("6f079930-661e-4639-ab70-502bb8265076") # uuid5 namespace for observation IDs

def generate_id(
    device_id: str,
    *,
    idempotency_key: str | None = None,
) -> str:
    """Deterministic ID for one observation (one Sample / device message).

    Same inputs → same ID, so replays are detectable. Prefers a client-supplied
    idempotency_key; otherwise derives identity from (device_id, ts).
    """
    identity = idempotency_key if idempotency_key is not None else f"{device_id}"
    return str(uuid.uuid5(_OBSERVATION_NS, identity))
