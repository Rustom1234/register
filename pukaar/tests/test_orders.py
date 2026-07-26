"""Routing + order building: conservative defaults are enforced in code."""

from pukaar.backends import BackendError, MockBackend
from pukaar.orders import build_order, route


class BrokenBackend(MockBackend):
    name = "broken"

    def route(self, case):
        raise BackendError("down")

    def assess_medical(self, case):
        raise BackendError("down")


def _case(**kw):
    base = {"category": None, "category_conf": 0.0, "detail": "", "urgency": "medium",
            "landmark_text": None, "freshness_min": 10}
    base.update(kw)
    return base


def test_confident_category_routes_in_code():
    r = route(_case(category="food", category_conf=1.0), MockBackend())
    assert r["primary"] == "food" and r["by"] == "code"


def test_ambiguous_routes_via_backend():
    r = route(_case(detail="thand lag rahi hai kambal chahiye"), MockBackend())
    assert r["primary"] == "shelter" and r["by"].startswith("agent")


def test_backend_failure_falls_back_flagged():
    r = route(_case(detail="whatever"), BrokenBackend())
    assert r["needs_review"] is True


def test_medical_low_confidence_forces_clinical_flag():
    class Overconfident(MockBackend):
        def assess_medical(self, case):
            return {"clinical_flag": False, "priority": "P3",
                    "instruction_ids": ["GI-1"], "confidence": 0.5}

    order = build_order(_case(category="medical", category_conf=1.0),
                        {"primary": "medical", "addons": [], "confidence": 1.0, "by": "code"},
                        Overconfident())
    assert order["clinical_flag"] is True   # code floor beats the model's optimism


def test_medical_backend_failure_is_conservative():
    order = build_order(_case(category="medical", category_conf=1.0),
                        {"primary": "medical", "addons": [], "confidence": 1.0, "by": "code"},
                        BrokenBackend())
    assert order["clinical_flag"] is True
    assert order["needs_review"] is True
    assert order["sku"] == "MED-1"


def test_addons_add_instructions():
    order = build_order(_case(category="shelter", category_conf=1.0),
                        {"primary": "shelter", "addons": ["food"], "confidence": 0.9, "by": "code"},
                        MockBackend())
    assert order["sku"] == "SEAS-M"
    assert "FI-2" in order["instruction_ids"]
