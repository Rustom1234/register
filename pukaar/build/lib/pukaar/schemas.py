"""JSON Schemas for every model call (structured outputs).

Schema enforcement is both a correctness tool and an injection defense
(OWASP LLM01; build plan §5): witness content can say anything, but the
model can only ever answer in these shapes. All schemas set
additionalProperties=false and list every property as required (optional
semantics are expressed with null-able types), per the structured-outputs
contract.
"""

from __future__ import annotations

CATEGORIES = ["medical", "food", "shelter"]

EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["category", "landmark_text", "freshness_min", "detail", "confidence"],
    "properties": {
        "category": {"anyOf": [{"type": "string", "enum": CATEGORIES}, {"type": "null"}]},
        "landmark_text": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "freshness_min": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "detail": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "confidence": {"type": "number"},
    },
}

ROUTE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["primary", "addons", "confidence"],
    "properties": {
        "primary": {"type": "string", "enum": CATEGORIES},
        "addons": {"type": "array", "items": {"type": "string", "enum": CATEGORIES}},
        "confidence": {"type": "number"},
    },
}

MEDICAL_ASSESS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["clinical_flag", "priority", "instruction_ids", "confidence"],
    "properties": {
        "clinical_flag": {"type": "boolean"},
        "priority": {"type": "string", "enum": ["P1", "P2", "P3"]},
        "instruction_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
    },
}

PHOTO_ASSIST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["category_hint", "urgency_hint", "confidence"],
    "properties": {
        "category_hint": {"anyOf": [{"type": "string", "enum": CATEGORIES}, {"type": "null"}]},
        "urgency_hint": {"type": "string", "enum": ["low", "medium", "high"]},
        "confidence": {"type": "number"},
    },
}


def validate(payload: dict, schema: dict) -> dict:
    """Minimal structural validation for mock-backend outputs and defense in
    depth on live outputs (the API already enforces the schema server-side)."""
    for key in schema["required"]:
        if key not in payload:
            raise ValueError(f"missing key: {key}")
    extra = set(payload) - set(schema["properties"])
    if extra:
        raise ValueError(f"unexpected keys: {sorted(extra)}")
    return payload
