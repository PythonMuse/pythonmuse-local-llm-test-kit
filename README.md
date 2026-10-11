# PythonMuse Local LLM Test Kit

A small, runnable companion to PythonMuse Article 41, [If the Data Can't Leave, Bring the Model In](https://github.com/PythonMuse/ai-ledger/blob/main/articles/41-bring-the-model-in/README.md).

The article's practical advice is to **test on work you have already finished**. Take one narrow task from completed engagements, run it through the models you can use, and score the output against what the valuation professional actually produced. This kit lets you practice that method on fictional deal documents before you try it on your own.

It has:

- **Synthetic engagement documents.** Each engagement has a term sheet, an executed financing agreement, an engagement letter, and a cap table.
- **An answer key with citations.** It records the right answer for every field and which documents are acceptable support for it.
- **A scoring rubric (CSV)** with the pass bar a valuation specialist sets *before* testing starts.
- **A Python runner.** It sends each engagement to a model running locally through [Ollama](https://ollama.com)'s REST API, scores the answers, and runs a deterministic cap-table check in Python.

Nothing in this kit leaves your machine when you run it against Ollama. The runner talks only to `http://localhost:11434`.

## The one narrow task

For each engagement, the model is asked to extract five fields about the preferred stock issued in that financing, and to cite the document each one came from:

| Field | Example |
|---|---|
| `liq_pref_multiple` | 1x |
| `participation` | non-participating, participating, or participating with a cap |
| `conversion_ratio` | 1:1 |
| `valuation_date` | 2026-03-31 |
| `preferred_shares_issued` | 2,000,000 |

The model's role is **retrieve and cite, never calculate**. It is told plainly that `INSUFFICIENT_EVIDENCE` is an acceptable answer. Outstanding shares are **not** asked of the model; Python sums them from the cap table.

## Practice set and scoring set

Engagements are split into two sets, on purpose:

- `engagements/practice/` (P01–P02): tune your prompt here as often as you like.
- `engagements/scoring/` (S01–S04): score here, and only score here.

You don't test a control with the same sample you used to design it. If you tune the prompt until the scoring set passes, you have measured how well you fit the prompt to those four engagements, not how well the model does the work. The runner enforces this: it evaluates the pass bar on the scoring set only.

With your own engagements, start with perhaps 5 to 10 on one task type and widen to 50 to 100 before anything goes into production. Those are practical sizes, not a statistical sample.

## Quick start

Requires Python 3.9+. The runner uses only the standard library; `pytest` is needed only for the tests.

**Without Ollama:** replay the hand-written example responses to see the scoring work:

```bash
python run_test.py --replay recorded_responses/example-small-local --set scoring
python run_test.py --replay recorded_responses/example-large-local --set scoring
```

**With Ollama:** install it, pull a model, then:

```bash
ollama pull qwen3:8b
python run_test.py --model qwen3:8b --set practice   # tune here
python run_test.py --model qwen3:8b --set scoring    # then score here
```

`qwen3:8b` is only an example, not a recommendation. Before using any model for work, check its license. Some open-weight models use Apache 2.0, while others use custom licenses with use restrictions. Check your organization's approval too, and confirm the laptop itself is approved to hold the test material.

Results are written to `results/` as two CSVs per run:

- `<model>__<set>__fields.csv`: one row per field, with the answer, citation, invented and correction flags.
- `<model>__<set>__engagements.csv`: run time, the Python cap-table check, and blank columns for the reviewer to record **minutes saved** and **cost to run**. For a local model, cost means hardware, power, and staff time to maintain it, not a per-use fee.

Run the tests:

```bash
pip install -r requirements.txt
python -m pytest
```

## What gets scored

From `scoring/scoring_rubric.csv`:

| Question | How | Pass bar |
|---|---|---|
| Did it get the answer right? | Normalized match to the key. A correct refusal counts as right. | ≥ 95% |
| Did it cite the correct source? | Cited document is one the key accepts. Scored only when both the key and the model gave a real answer. | ≥ 95% |
| Did it invent anything? | Answered where the key says refuse, or cited a document outside the authorized set (including ones that don't exist). | 0 |
| How often would an analyst correct it? | Fields with a wrong answer or a wrong citation. | recorded |
| How much time did it save? | Recorded by the reviewer. | recorded |
| What did it cost to run? | Recorded by the reviewer. | recorded |

The pass bar values are an example. In a real test, **the valuation specialist sets them before testing starts**, not the person adjusting the prompts.

## The seeded exceptions

The scoring engagements are built to trigger specific failures. These are not mistakes. **Do not "fix" them** by editing the sample data; that would delete the point of the kit. `tests/test_kit.py` asserts each one.

| Engagement | What's seeded | What a good answer does |
|---|---|---|
| S01 Brightwater Analytics | A term sheet from a **different client** (Harrowgate Foods, 2x participating) has been misfiled in this folder. It is not in `manifest.csv`. | Never sees it. The permission filter in `testkit/retrieval.py` loads only manifest-listed documents, so the misfiled file never reaches the prompt. Folder location is not permission. |
| S02 Cinderpath Logistics | The non-binding term sheet says **1x**. The executed agreement says **1.5x**. | Answers 1.5x and cites the financing agreement. Citing the term sheet is scored wrong here. |
| S03 Driftwood Materials | The engagement letter says the valuation date **has not been agreed**. Conversion is **1:1.25**, not 1:1. | Answers `INSUFFICIENT_EVIDENCE` for the date. Any date is invented. |
| S04 Emberline Software | The agreement issued **2,500,000** Series A shares. The cap table still shows **2,000,000**. | Extracts 2,500,000 from the agreement. Python then reports a 500,000-share cap-table break. |

## The two example models

`recorded_responses/` holds **hand-written, illustrative responses, not output from any real model**. They exist so you can see the scoring without installing anything, and so the tests have fixed inputs. The names are labels, not products.

| | example-small-local | example-large-local |
|---|---|---|
| Right answer | 16/20 (80.0%) | 20/20 (100.0%) |
| Correct citation | 16/19 (84.2%) | 18/19 (94.7%) |
| Invented anything | 1 (gave a date for S03) | 1 (cited `deal_summary.md`, which does not exist) |
| Corrections | 5 | 1 |
| Run time | 156.0 s | 581.0 s |
| S04 cap-table check | TIES | BREAK, +500,000 |
| Meets pass bar | No | No |

Two lessons are worth noticing:

1. **The large model got every answer right and still failed.** It cited a document that doesn't exist. A perfect answer with an invented source is still an invented source, and a reviewer who trusts the citation would go looking for a file that was never there.
2. **The small model's S04 cap-table check ties, and that's bad news.** It read the share count from the cap table instead of the agreement, so of course it ties to the cap table. A tie-out built on a wrong extraction ties to the wrong number. That is why the scorer compares against known answers rather than against the documents the model chose to read.

## Using it on your own work

1. Copy the folder structure for your own completed engagements, using material approved for the test (redacted or synthesized where necessary).
2. List each engagement's authorized documents in `engagements/manifest.csv`.
3. Write the answer key from what the specialist actually concluded, with acceptable sources.
4. Have the specialist set the pass bar in `scoring/scoring_rubric.csv` **before** the first run.
5. Tune on practice, score on scoring, and record minutes saved and cost to run.

## Limits

- This is a teaching example, not a validated testing tool. The normalizers handle the formats in this kit; your own documents will need their own.
- The permission filter here is a manifest. In a real system, retrieval has to enforce your actual document-level permissions (ethical walls included) before anything reaches the model.
- A model that passes this kit has passed four fictional engagements. It has not been approved for anything.

## License

Code (`.py` files) is MIT; see `LICENSE`. Written content and sample data (Markdown, CSV, JSON) are CC BY-NC-SA 4.0; see `LICENSE-CONTENT`. Every company, person, figure, and term in this repository is fictional.

## About this repository

Built as a companion to PythonMuse Article 41. Claude Sonnet and Claude Opus reviewed the article draft and shaped the test design. Claude Code (Claude Opus 5.5) built the documents, answer key, runner, and tests.
