from datetime import datetime
import uuid

def create_event(
    event,
    data=None,
    error=None,
    trace_id=None,
    span_id=None,
    parent_span_id=None,
    source=None
):
    return {
        "event_id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "source": source or {},
        "data": data or {},
        "meta": {},
        "error": error
    }
