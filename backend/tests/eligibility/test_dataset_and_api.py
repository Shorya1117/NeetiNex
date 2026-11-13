"""Tests on the REAL generated dataset + API endpoints."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routers.eligibility import router
from backend.services.eligibility.dataset_service import DATASET_PATH
from backend.services.eligibility.field_catalog import FIELD_CATALOG
from backend.services.eligibility.rule_evaluator import OPERATORS

pytestmark = pytest.mark.skipif(
    not DATASET_PATH.exists(),
    reason="run: python -m backend.ingestion.eligibility_structuring.build_eligibility_dataset")


@pytest.fixture(scope="module")
def dataset():
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))["schemes"]


@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_no_scheme_discarded(dataset):
    assert len(dataset) == 192
    assert len({s["scheme_id"] for s in dataset}) == 192


def test_every_scheme_has_source_and_text(dataset):
    for s in dataset:
        assert s["source"]["source_url"] and s["original_eligibility_text"].strip()


def test_nothing_marked_verified_automatically(dataset):
    assert all(s["source"]["verification_status"] == "extracted_unverified" for s in dataset)


def test_rules_are_well_formed(dataset):
    for s in dataset:
        for r in s["conditions"]["rules"]:
            assert r["source_text"]
            if r["kind"] == "condition":
                assert r["operator"] in OPERATORS and r["field"] in FIELD_CATALOG


def test_schemes_endpoint(client):
    r = client.get("/api/eligibility/schemes")
    assert r.status_code == 200 and len(r.json()) == 192


def test_criteria_endpoint_and_404(client):
    sid = client.get("/api/eligibility/schemes").json()[0]["scheme_id"]
    assert client.get(f"/api/eligibility/{sid}/criteria").status_code == 200
    assert client.get("/api/eligibility/nope/criteria").status_code == 404


def test_check_endpoint_validation(client):
    sid = client.get("/api/eligibility/schemes").json()[0]["scheme_id"]
    assert client.post("/api/eligibility/check",
                       json={"scheme_id": sid, "user_profile": {"age": -3}}).status_code == 422
    assert client.post("/api/eligibility/check",
                       json={"scheme_id": "nope", "user_profile": {}}).status_code == 404
    ok = client.post("/api/eligibility/check", json={"scheme_id": sid, "user_profile": {}})
    assert ok.status_code == 200 and ok.json()["eligible"] is False


def test_missing_information_endpoint(client):
    schemes = client.get("/api/eligibility/schemes").json()
    s = next(x for x in schemes if x["required_fields"])
    r = client.post("/api/eligibility/missing-information",
                    json={"scheme_id": s["scheme_id"], "user_profile": {}}).json()
    assert [f["field"] for f in r["missing_fields"]] == s["required_fields"]


def test_check_multiple_counts(client):
    r = client.post("/api/eligibility/check-multiple",
                    json={"user_profile": {"age": 30, "state": "Rajasthan"}}).json()
    assert r["total_schemes_evaluated"] == 192
    assert sum(r["counts"].values()) == 192


def test_astha_card_real_scheme(client):
    """Astha Card: native of Rajasthan, 40% disability, income <= 1.20 lakh."""
    schemes = client.get("/api/eligibility/schemes").json()
    sid = next(s["scheme_id"] for s in schemes if s["scheme_name"] == "Astha Card Scheme")
    base = {"state": "Rajasthan", "disability_status": True, "disability_percentage": 50}
    over = client.post("/api/eligibility/check", json={
        "scheme_id": sid, "user_profile": {**base, "annual_income": 300000}}).json()
    assert over["overall_status"] == "NOT_ELIGIBLE"
    ok = client.post("/api/eligibility/check", json={
        "scheme_id": sid, "user_profile": {**base, "annual_income": 100000}}).json()
    assert ok["overall_status"] in ("ELIGIBLE", "UNVERIFIED")  # unverified: manual line remains
