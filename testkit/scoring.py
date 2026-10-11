"""Score a model's extraction against the answer key, then against the pass bar.

The questions are the article's scorecard:
  Did it get the answer right?      -> answer_correct
  Did it cite the correct source?   -> citation_correct
  Did it invent anything?           -> invented
  How often would an analyst correct it? -> correction_needed
Time saved and cost to run are recorded by the reviewer, not computed here.
"""

import csv
import json
import re
from datetime import datetime

from .prompt import FIELDS, REFUSAL

# --------------------------------------------------------------------------
# Normalization: compare meaning, not formatting.
# --------------------------------------------------------------------------

_DATE_FORMATS = ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%d %B %Y")


def is_refusal(value):
    return value is not None and "INSUFFICIENT" in str(value).upper()


def _norm_multiple(v):
    m = re.search(r"\d+(?:\.\d+)?", v)
    return float(m.group()) if m else None


def _norm_participation(v):
    s = v.lower()
    if "particip" not in s:
        return None
    if "non" in s:
        return "non-participating"
    uncapped = any(w in s for w in ("no cap", "uncapped", "without", "full"))
    if "cap" in s and not uncapped:
        return "participating-capped"
    return "participating"


def _norm_ratio(v):
    m = re.search(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)", v)
    if not m:
        return None
    left, right = float(m.group(1)), float(m.group(2))
    return round(right / left, 6) if left else None


def _norm_date(v):
    s = v.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _norm_shares(v):
    digits = re.sub(r"[^\d]", "", v.split(".")[0])
    return int(digits) if digits else None


_NORMALIZERS = {
    "liq_pref_multiple": _norm_multiple,
    "participation": _norm_participation,
    "conversion_ratio": _norm_ratio,
    "valuation_date": _norm_date,
    "preferred_shares_issued": _norm_shares,
}


def normalize(field, value):
    """Return a comparable form of `value`, REFUSAL for a refusal, or None if
    the value is missing or cannot be read."""
    if value is None or str(value).strip() == "":
        return None
    if is_refusal(value):
        return REFUSAL
    return _NORMALIZERS[field](str(value))


# --------------------------------------------------------------------------
# Parsing the model's response
# --------------------------------------------------------------------------

def parse_response(ollama_response):
    """Pull {field: {"value": ..., "source_document": ...}} out of an Ollama
    /api/chat response. Malformed JSON yields an empty dict, so every field
    scores as unanswered rather than crashing the run."""
    content = (ollama_response.get("message") or {}).get("content", "")
    try:
        data = json.loads(content)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def duration_seconds(ollama_response):
    ns = ollama_response.get("total_duration")
    return round(ns / 1e9, 1) if isinstance(ns, (int, float)) else None


# --------------------------------------------------------------------------
# Answer key and per-field scoring
# --------------------------------------------------------------------------

def load_answer_key(path):
    """{engagement_id: {field: row}}"""
    key = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["acceptable_sources"] = [s for s in row["acceptable_sources"].split("|") if s]
            key.setdefault(row["engagement_id"], {})[row["field"]] = row
    return key


def score_field(field, key_row, model_item, authorized_ids):
    model_item = model_item if isinstance(model_item, dict) else {}
    raw_value = model_item.get("value")
    source = (model_item.get("source_document") or "").strip()

    expected = normalize(field, key_row["expected_value"])
    got = normalize(field, raw_value)
    answer_correct = got is not None and got == expected

    # Citations are scored only when both the key and the model gave a real
    # answer. "When it answers, does it point at the right document?"
    citation_scored = expected != REFUSAL and got not in (None, REFUSAL)
    citation_correct = (source in key_row["acceptable_sources"]) if citation_scored else None

    invented_value = expected == REFUSAL and got not in (None, REFUSAL)
    invented_source = bool(source) and got != REFUSAL and source not in authorized_ids
    invented = invented_value or invented_source

    correction_needed = (not answer_correct) or citation_correct is False
    return {
        "field": field,
        "expected": key_row["expected_value"],
        "model_value": "" if raw_value is None else str(raw_value),
        "model_source": source,
        "answer_correct": answer_correct,
        "citation_correct": citation_correct,
        "invented": invented,
        "correction_needed": correction_needed,
    }


def score_engagement(engagement_id, answer_key, parsed, authorized_ids):
    rows = []
    for field in FIELDS:
        r = score_field(field, answer_key[engagement_id][field], parsed.get(field),
                        set(authorized_ids))
        r["engagement_id"] = engagement_id
        rows.append(r)
    return rows


def summarize(field_rows):
    fields = len(field_rows)
    answers = sum(r["answer_correct"] for r in field_rows)
    cit_scored = [r for r in field_rows if r["citation_correct"] is not None]
    cit_ok = sum(r["citation_correct"] for r in cit_scored)
    return {
        "fields_scored": fields,
        "answers_correct": answers,
        "answer_accuracy": round(answers / fields, 4) if fields else 0.0,
        "citations_scored": len(cit_scored),
        "citations_correct": cit_ok,
        "citation_accuracy": round(cit_ok / len(cit_scored), 4) if cit_scored else 0.0,
        "invented": sum(r["invented"] for r in field_rows),
        "corrections_needed": sum(r["correction_needed"] for r in field_rows),
    }


# --------------------------------------------------------------------------
# Pass bar (set by the specialist in scoring/scoring_rubric.csv)
# --------------------------------------------------------------------------

_METRIC_FOR = {
    "answer_correct": "answer_accuracy",
    "citation_correct": "citation_accuracy",
    "invented": "invented",
}

_OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}


def load_rubric(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def evaluate_pass_bar(summary, rubric):
    """Return (passed, [check dicts]). Rubric rows marked 'recorded' are
    filled in by the reviewer and are not auto-evaluated."""
    checks = []
    for row in rubric:
        bar = row["pass_bar"].strip()
        metric = _METRIC_FOR.get(row["criterion_id"])
        if metric is None or bar == "recorded":
            continue
        op, threshold = bar.split()
        actual = summary[metric]
        checks.append({
            "criterion": row["criterion"],
            "metric": metric,
            "actual": actual,
            "bar": bar,
            "passed": _OPS[op](actual, float(threshold)),
        })
    return all(c["passed"] for c in checks), checks
