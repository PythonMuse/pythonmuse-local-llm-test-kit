"""Run the PythonMuse Local LLM Test Kit.

Against a local model through Ollama:
    python run_test.py --model qwen3:8b --set practice
    python run_test.py --model qwen3:8b --set scoring

Without Ollama, replaying the hand-written example responses:
    python run_test.py --replay recorded_responses/example-small-local --set scoring

Tune your prompt on the practice set. Score on the scoring set. Never the
other way round.
"""

import argparse
import csv
import re
import sys
from pathlib import Path

from testkit import deterministic, retrieval, scoring
from testkit.ollama_client import DEFAULT_HOST, OllamaClient, ReplayClient
from testkit.prompt import RESPONSE_SCHEMA, build_messages

HERE = Path(__file__).resolve().parent
ENGAGEMENTS = HERE / "engagements"
MANIFEST = ENGAGEMENTS / "manifest.csv"
ANSWER_KEY = HERE / "answer_key" / "answer_key.csv"
RUBRIC = HERE / "scoring" / "scoring_rubric.csv"

FIELD_COLUMNS = ["engagement_id", "field", "expected", "model_value", "model_source",
                 "answer_correct", "citation_correct", "invented", "correction_needed"]
ENGAGEMENT_COLUMNS = ["engagement_id", "client", "seconds", "outstanding_shares_python",
                      "cap_table_preferred", "extracted_preferred", "cap_table_difference",
                      "cap_table_check", "analyst_minutes_manual", "analyst_minutes_with_ai",
                      "run_cost_note"]


def run(client, set_name, results_dir=None):
    """Run one model over one set. Returns (summary, field_rows, engagement_rows,
    passed, checks). `passed` is None for the practice set."""
    manifest = retrieval.load_manifest(MANIFEST)
    key = scoring.load_answer_key(ANSWER_KEY)
    field_rows, engagement_rows = [], []

    for eid in retrieval.engagement_ids(manifest, set_name):
        info = retrieval.engagement_info(manifest, eid)
        docs = retrieval.authorized_documents(manifest, eid, ENGAGEMENTS)
        response = client.chat(eid, build_messages(eid, docs), RESPONSE_SCHEMA)
        parsed = scoring.parse_response(response)
        field_rows.extend(scoring.score_engagement(eid, key, parsed, docs.keys()))

        cap_path = next(ENGAGEMENTS / r["path"] for r in manifest
                        if r["engagement_id"] == eid and r["document_id"] == "cap_table.csv")
        extracted = scoring.normalize(
            "preferred_shares_issued",
            (parsed.get("preferred_shares_issued") or {}).get("value"))
        check = deterministic.cap_table_check(
            cap_path, info["series_name"],
            extracted if isinstance(extracted, int) else None)
        engagement_rows.append({
            "engagement_id": eid,
            "client": info["client"],
            "seconds": scoring.duration_seconds(response),
            "outstanding_shares_python": deterministic.outstanding_shares(cap_path),
            "cap_table_preferred": check["cap_table_preferred"],
            "extracted_preferred": check["extracted_preferred"],
            "cap_table_difference": check["difference"],
            "cap_table_check": check["status"],
            # Filled in by the reviewer:
            "analyst_minutes_manual": "",
            "analyst_minutes_with_ai": "",
            "run_cost_note": "",
        })

    summary = scoring.summarize(field_rows)
    if set_name == "scoring":
        passed, checks = scoring.evaluate_pass_bar(summary, scoring.load_rubric(RUBRIC))
    else:
        passed, checks = None, []

    if results_dir:
        write_results(Path(results_dir), client.model, set_name, field_rows, engagement_rows)
    return summary, field_rows, engagement_rows, passed, checks


def write_results(results_dir, model, set_name, field_rows, engagement_rows):
    results_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{re.sub(r'[^A-Za-z0-9._-]', '_', model)}__{set_name}"
    for suffix, cols, rows in (("fields", FIELD_COLUMNS, field_rows),
                               ("engagements", ENGAGEMENT_COLUMNS, engagement_rows)):
        with open(results_dir / f"{stem}__{suffix}.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)


def print_report(model, set_name, summary, engagement_rows, passed, checks):
    print(f"\nModel: {model}    Set: {set_name}")
    print(f"  Right answer:      {summary['answers_correct']}/{summary['fields_scored']}"
          f"  ({summary['answer_accuracy']:.1%})")
    print(f"  Correct citation:  {summary['citations_correct']}/{summary['citations_scored']}"
          f"  ({summary['citation_accuracy']:.1%})")
    print(f"  Invented anything: {summary['invented']}")
    print(f"  Corrections an analyst would make: {summary['corrections_needed']}")
    secs = [r["seconds"] for r in engagement_rows if r["seconds"] is not None]
    if secs:
        print(f"  Model run time:    {sum(secs):.1f} seconds across {len(secs)} engagements")
    print("  Cap-table check (Python, not the model):")
    for r in engagement_rows:
        diff = r["cap_table_difference"]
        extra = f" (difference {diff:+,})" if diff else ""
        print(f"    {r['engagement_id']}: {r['cap_table_check']}{extra}; "
              f"outstanding shares {r['outstanding_shares_python']:,}")
    if passed is None:
        print("  Pass bar: not evaluated. This is the practice set -- tune here, score on 'scoring'.")
    else:
        for c in checks:
            mark = "PASS" if c["passed"] else "FAIL"
            print(f"  [{mark}] {c['criterion']}  actual {c['actual']}, bar {c['bar']}")
        print(f"  RESULT: {'MEETS' if passed else 'DOES NOT MEET'} the specialist's pass bar")
    print("  Time saved and cost to run: fill in the engagements results file.")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--model", help="Ollama model name, e.g. qwen3:8b")
    src.add_argument("--replay", help="Folder of recorded responses instead of a live model")
    p.add_argument("--set", choices=["practice", "scoring"], default="practice")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--results", default=str(HERE / "results"))
    args = p.parse_args(argv)

    client = ReplayClient(args.replay) if args.replay else OllamaClient(args.model, args.host)
    summary, _, engagement_rows, passed, checks = run(client, args.set, args.results)
    print_report(client.model, args.set, summary, engagement_rows, passed, checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
