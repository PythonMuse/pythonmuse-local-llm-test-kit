"""Tests for the PythonMuse Local LLM Test Kit.

Every expected figure below was calculated by hand from the synthetic
documents and the recorded responses before the assertion was written. See
README.md, "The seeded exceptions", for the reasoning behind each one.
"""

import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run_test  # noqa: E402
from testkit import deterministic, retrieval, scoring  # noqa: E402
from testkit.ollama_client import OllamaClient, ReplayClient  # noqa: E402
from testkit.prompt import FIELDS, REFUSAL, RESPONSE_SCHEMA, build_messages  # noqa: E402

ENG = ROOT / "engagements"
MANIFEST = retrieval.load_manifest(ENG / "manifest.csv")
KEY = scoring.load_answer_key(ROOT / "answer_key" / "answer_key.csv")
RUBRIC = scoring.load_rubric(ROOT / "scoring" / "scoring_rubric.csv")


def cap_path(eid):
    return next(ENG / r["path"] for r in MANIFEST
                if r["engagement_id"] == eid and r["document_id"] == "cap_table.csv")


# ---------------------------------------------------------------------------
# Data integrity: the kit's own fixtures
# ---------------------------------------------------------------------------

def test_sets_are_separate():
    assert retrieval.engagement_ids(MANIFEST, "practice") == ["P01", "P02"]
    assert retrieval.engagement_ids(MANIFEST, "scoring") == ["S01", "S02", "S03", "S04"]


def test_answer_key_covers_every_engagement_and_cites_only_manifest_docs():
    for eid in retrieval.engagement_ids(MANIFEST, "practice") + \
            retrieval.engagement_ids(MANIFEST, "scoring"):
        assert set(KEY[eid]) == set(FIELDS)
        allowed = {r["document_id"] for r in MANIFEST if r["engagement_id"] == eid}
        for row in KEY[eid].values():
            assert set(row["acceptable_sources"]) <= allowed


def test_seeded_exceptions_are_still_in_the_documents():
    """Guard against someone 'fixing' the sample data."""
    s02 = ENG / "scoring" / "S02-cinderpath-logistics"
    assert "| 5 | Liquidation preference | 1x" in (s02 / "term_sheet.md").read_text(encoding="utf-8")
    assert "(1.5x)" in (s02 / "financing_agreement.md").read_text(encoding="utf-8")

    s03 = ENG / "scoring" / "S03-driftwood-materials"
    assert "no valuation date has been agreed" in (s03 / "engagement_letter.md").read_text(encoding="utf-8")
    assert "1:1.25" in (s03 / "financing_agreement.md").read_text(encoding="utf-8")

    s04 = ENG / "scoring" / "S04-emberline-software"
    assert "**2,500,000 shares**" in (s04 / "financing_agreement.md").read_text(encoding="utf-8")
    assert deterministic.series_shares(s04 / "cap_table.csv", "Series A Preferred Stock") == 2_000_000


# ---------------------------------------------------------------------------
# Permission-aware retrieval: the filter sits before the model
# ---------------------------------------------------------------------------

def test_misfiled_document_exists_on_disk_but_never_reaches_the_prompt():
    decoy = ENG / "scoring" / "S01-brightwater-analytics" / "misfiled_harrowgate_foods_term_sheet.md"
    assert decoy.exists()  # otherwise this test proves nothing

    docs = retrieval.authorized_documents(MANIFEST, "S01", ENG)
    assert set(docs) == {"term_sheet.md", "financing_agreement.md",
                         "engagement_letter.md", "cap_table.csv"}
    for eid in retrieval.engagement_ids(MANIFEST, "scoring"):
        prompt = json.dumps(build_messages(eid, retrieval.authorized_documents(MANIFEST, eid, ENG)))
        assert "Harrowgate" not in prompt


def test_manifest_mixing_clients_is_refused():
    bad = [dict(r) for r in MANIFEST if r["engagement_id"] == "S01"]
    bad[0]["client"] = "Harrowgate Foods, Inc."
    with pytest.raises(PermissionError):
        retrieval.authorized_documents(bad, "S01", ENG)


def test_manifest_reaching_into_another_engagement_folder_is_refused():
    bad = [dict(r) for r in MANIFEST if r["engagement_id"] == "S01"]
    bad[0]["path"] = "scoring/S02-cinderpath-logistics/term_sheet.md"
    with pytest.raises(PermissionError):
        retrieval.authorized_documents(bad, "S01", ENG)


def test_manifest_path_outside_engagements_is_refused():
    bad = [dict(r) for r in MANIFEST if r["engagement_id"] == "S01"]
    for r in bad:
        r["path"] = "../README.md"
    with pytest.raises(PermissionError):
        retrieval.authorized_documents(bad, "S01", ENG)


# ---------------------------------------------------------------------------
# Deterministic calculations: Python adds up, not the model
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eid, expected", [
    ("P01", 7_000_000 + 3_000_000),
    ("P02", 6_000_000 + 2_500_000 + 1_500_000),
    ("S01", 8_150_000 + 2_000_000),
    ("S02", 5_400_000 + 2_200_000 + 1_800_000),
    ("S03", 4_800_000 + 1_600_000),
    ("S04", 7_500_000 + 2_000_000),
])
def test_outstanding_shares_excludes_option_pool(eid, expected):
    assert deterministic.outstanding_shares(cap_path(eid)) == expected


def test_cap_table_check_finds_the_s04_break():
    r = deterministic.cap_table_check(cap_path("S04"), "Series A Preferred Stock", 2_500_000)
    assert r == {"cap_table_preferred": 2_000_000, "extracted_preferred": 2_500_000,
                 "difference": 500_000, "status": "BREAK"}


def test_cap_table_check_ties_on_a_wrong_extraction():
    """A tie built on a wrong extraction ties to the wrong number."""
    r = deterministic.cap_table_check(cap_path("S04"), "Series A Preferred Stock", 2_000_000)
    assert r["status"] == "TIES"


def test_cap_table_check_not_checked_without_a_number():
    r = deterministic.cap_table_check(cap_path("S04"), "Series A Preferred Stock", None)
    assert r["status"] == "NOT_CHECKED"


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field, raw, expected", [
    ("liq_pref_multiple", "1.5x", 1.5),
    ("liq_pref_multiple", "one times (1x)", 1.0),
    ("participation", "non-participating", "non-participating"),
    ("participation", "participating (no cap)", "participating"),
    ("participation", "participating, capped at 3x", "participating-capped"),
    ("participation", "Participating without any cap", "participating"),
    ("conversion_ratio", "1:1.25", 1.25),
    ("conversion_ratio", "1 : 1", 1.0),
    ("valuation_date", "March 31, 2026", "2026-03-31"),
    ("valuation_date", "06/30/2026", "2026-06-30"),
    ("preferred_shares_issued", "2,500,000 shares", 2_500_000),
    ("valuation_date", "Insufficient evidence", REFUSAL),
    ("valuation_date", "", None),
    ("valuation_date", "sometime in spring", None),
])
def test_normalize(field, raw, expected):
    assert scoring.normalize(field, raw) == expected


# ---------------------------------------------------------------------------
# Per-field scoring rules
# ---------------------------------------------------------------------------

AUTH = {"term_sheet.md", "financing_agreement.md", "engagement_letter.md", "cap_table.csv"}


def test_correct_refusal_is_a_right_answer_and_not_citation_scored():
    r = scoring.score_field("valuation_date", KEY["S03"]["valuation_date"],
                            {"value": REFUSAL, "source_document": ""}, AUTH)
    assert r["answer_correct"] is True
    assert r["citation_correct"] is None
    assert r["invented"] is False
    assert r["correction_needed"] is False


def test_answering_when_the_key_says_refuse_is_invented():
    r = scoring.score_field("valuation_date", KEY["S03"]["valuation_date"],
                            {"value": "2026-03-31", "source_document": "engagement_letter.md"}, AUTH)
    assert (r["answer_correct"], r["invented"], r["correction_needed"]) == (False, True, True)


def test_citing_a_document_outside_the_authorized_set_is_invented():
    r = scoring.score_field("participation", KEY["S01"]["participation"],
                            {"value": "non-participating", "source_document": "deal_summary.md"}, AUTH)
    assert r["answer_correct"] is True
    assert r["citation_correct"] is False
    assert r["invented"] is True


def test_term_sheet_is_not_an_acceptable_source_where_it_conflicts():
    r = scoring.score_field("liq_pref_multiple", KEY["S02"]["liq_pref_multiple"],
                            {"value": "1x", "source_document": "term_sheet.md"}, AUTH)
    assert (r["answer_correct"], r["citation_correct"], r["invented"]) == (False, False, False)


def test_refusing_when_the_answer_exists_is_wrong_but_not_invented():
    r = scoring.score_field("liq_pref_multiple", KEY["S01"]["liq_pref_multiple"],
                            {"value": REFUSAL, "source_document": ""}, AUTH)
    assert (r["answer_correct"], r["citation_correct"], r["invented"],
            r["correction_needed"]) == (False, None, False, True)


def test_malformed_model_output_scores_as_unanswered_not_crashed():
    parsed = scoring.parse_response({"message": {"content": "Sure! Here are the terms..."}})
    assert parsed == {}
    rows = scoring.score_engagement("S01", KEY, parsed, AUTH)
    s = scoring.summarize(rows)
    assert (s["answers_correct"], s["invented"], s["corrections_needed"]) == (0, 0, 5)


# ---------------------------------------------------------------------------
# End to end, replaying the hand-written example responses
# ---------------------------------------------------------------------------

def test_small_example_model_scores_as_hand_calculated(tmp_path):
    summary, _, eng_rows, passed, checks = run_test.run(
        ReplayClient(ROOT / "recorded_responses" / "example-small-local"), "scoring", tmp_path)
    # Wrong answers: S02 liq pref, S03 conversion, S03 valuation date, S04 shares -> 16/20.
    # Citation-scored: 20 fields minus S03 valuation date (key is a refusal) = 19.
    # Wrong citations: S01 val date (term sheet), S02 liq pref (term sheet), S04 shares (cap table) -> 16/19.
    # Invented: S03 valuation date. Corrections: the 4 wrong answers + S01 val date citation = 5.
    assert summary == {"fields_scored": 20, "answers_correct": 16, "answer_accuracy": 0.8,
                       "citations_scored": 19, "citations_correct": 16,
                       "citation_accuracy": round(16 / 19, 4), "invented": 1,
                       "corrections_needed": 5}
    assert passed is False
    assert [c["passed"] for c in checks] == [False, False, False]
    assert sum(r["seconds"] for r in eng_rows) == pytest.approx(38.4 + 41.1 + 36.9 + 39.6)
    s04 = next(r for r in eng_rows if r["engagement_id"] == "S04")
    assert s04["cap_table_check"] == "TIES"  # it read the cap table, so of course it ties
    assert (tmp_path / "example-small-local__scoring__fields.csv").exists()


def test_large_example_model_near_miss(tmp_path):
    summary, _, eng_rows, passed, checks = run_test.run(
        ReplayClient(ROOT / "recorded_responses" / "example-large-local"), "scoring", tmp_path)
    # Every answer right, but S01 participation cites a document that does not exist.
    assert summary == {"fields_scored": 20, "answers_correct": 20, "answer_accuracy": 1.0,
                       "citations_scored": 19, "citations_correct": 18,
                       "citation_accuracy": round(18 / 19, 4), "invented": 1,
                       "corrections_needed": 1}
    assert passed is False
    assert [(c["metric"], c["passed"]) for c in checks] == [
        ("answer_accuracy", True), ("citation_accuracy", False), ("invented", False)]
    s04 = next(r for r in eng_rows if r["engagement_id"] == "S04")
    assert (s04["cap_table_check"], s04["cap_table_difference"]) == ("BREAK", 500_000)


class KeyClient:
    """Answers straight from the answer key -- a perfect model."""
    model = "perfect-key"

    def chat(self, eid, messages, schema):
        content = {}
        for f in FIELDS:
            row = KEY[eid][f]
            src = row["acceptable_sources"][0] if row["acceptable_sources"] else ""
            content[f] = {"value": row["expected_value"], "source_document": src}
        return {"message": {"content": json.dumps(content)}, "total_duration": 1_000_000_000}


def test_perfect_model_meets_the_pass_bar(tmp_path):
    summary, _, _, passed, _ = run_test.run(KeyClient(), "scoring", tmp_path)
    assert (summary["answer_accuracy"], summary["citation_accuracy"], summary["invented"]) == (1.0, 1.0, 0)
    assert passed is True


def test_practice_set_is_never_judged_against_the_pass_bar(tmp_path):
    summary, _, _, passed, checks = run_test.run(KeyClient(), "practice", tmp_path)
    assert summary["fields_scored"] == 10
    assert passed is None and checks == []


# ---------------------------------------------------------------------------
# Ollama client: right endpoint, deterministic settings, nothing extra sent
# ---------------------------------------------------------------------------

def test_ollama_payload_settings():
    p = OllamaClient("qwen3:8b").build_payload([{"role": "user", "content": "x"}], RESPONSE_SCHEMA)
    assert p["model"] == "qwen3:8b"
    assert p["stream"] is False
    assert p["format"] == RESPONSE_SCHEMA
    assert p["options"] == {"temperature": 0, "seed": 42}


def test_ollama_chat_posts_to_local_api_with_only_authorized_docs(monkeypatch):
    captured = {}
    canned = {"message": {"role": "assistant", "content": "{}"}, "done": True}

    class FakeResp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResp(json.dumps(canned).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    docs = retrieval.authorized_documents(MANIFEST, "S01", ENG)
    out = OllamaClient("qwen3:8b").chat("S01", build_messages("S01", docs), RESPONSE_SCHEMA)

    assert out == canned
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["method"] == "POST"
    assert "Harrowgate" not in json.dumps(captured["body"])
    assert "Brightwater Analytics" in json.dumps(captured["body"])
