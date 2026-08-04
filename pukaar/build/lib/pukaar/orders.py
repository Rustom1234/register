"""Routing + order building (build plan §3.7–3.8).

Code routes when the category is confident; the model only handles
ambiguity. Conservative defaults are enforced HERE, in code, after any
model call — uncertainty always raises the clinical flag and priority,
never lowers it (the model can add caution but cannot remove ours).
"""

from __future__ import annotations

from . import strings
from .backends import Backend, BackendError

SEASON_SKU = "SEAS-M"  # monsoon demo; winter swaps to SEAS-W via config later


def route(case: dict, backend: Backend) -> dict:
    if case.get("category") and case.get("category_conf", 0) >= 0.8:
        return {"primary": case["category"], "addons": [], "confidence": case["category_conf"], "by": "code"}
    try:
        r = backend.route(case)
        return {**r, "by": f"agent:{backend.name}"}
    except BackendError:
        return {"primary": case.get("category") or "shelter", "addons": [],
                "confidence": 0.0, "by": "fallback", "needs_review": True}


def build_order(case: dict, routing: dict, backend: Backend) -> dict:
    primary = routing["primary"]
    addons = list(routing.get("addons", []))
    needs_review = bool(routing.get("needs_review"))
    clinical_flag = False
    priority = "P2"
    instruction_ids = ["GI-1"]
    confidence = routing.get("confidence", 0.5)

    if primary == "medical":
        try:
            a = backend.assess_medical(case)
            clinical_flag = a["clinical_flag"]
            priority = a["priority"]
            instruction_ids = a["instruction_ids"] or ["GI-1", "MI-1"]
            confidence = a["confidence"]
        except BackendError:
            a = None
            needs_review = True
            clinical_flag, priority, instruction_ids, confidence = True, "P2", ["GI-1", "MI-1", "MI-2"], 0.0
        # Conservative floor, enforced in code (never in prompts alone):
        # any wound/illness case with low confidence keeps the clinical flag up.
        if confidence < 0.8:
            clinical_flag = True
        if case.get("urgency") == "high" and priority == "P3":
            priority = "P2"
        sku = "MED-1"
    elif primary == "food":
        sku = "FOOD-1"
        instruction_ids = ["GI-1", "FI-1", "FI-2"]
        priority = "P1" if case.get("urgency") == "high" else "P2"
    else:  # shelter / weather
        sku = SEASON_SKU
        instruction_ids = ["GI-1", "SI-1", "SI-2"]
        priority = "P1" if case.get("urgency") == "high" else "P2"

    for cat in ("medical", "food", "shelter"):
        if cat in addons and cat != primary:
            instruction_ids.append({"medical": "MI-3", "food": "FI-2", "shelter": "SI-2"}[cat])

    return {
        "sku": sku,
        "addons": addons,
        "clinical_flag": clinical_flag,
        "priority": priority,
        "instruction_ids": instruction_ids,
        "confidence": confidence,
        "needs_review": needs_review,
        "created_by": f"agent:{primary}" if routing.get("by", "").startswith("agent") else f"code:{primary}",
        "kit": strings.KIT_SKUS[sku],
    }
