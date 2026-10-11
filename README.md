# PythonMuse Local LLM Test Kit

A small, runnable companion to PythonMuse Article 41, [If the Data Can't Leave, Bring the Model In](https://github.com/PythonMuse/ai-ledger/blob/main/articles/41-bring-the-model-in/README.md).

The article's practical advice is to **test on work you have already finished**. Take one narrow task from completed engagements, run it through the models you can use, and score the output against what the valuation professional actually produced. This kit lets you practice that method on fictional deal documents before you try it on your own.

It has:

- **Synthetic engagement documents.** Each engagement has a term sheet, an executed financing agreement, an engagement letter, and a cap table.
- **An answer key with citations.** It records the right answer for every field and which documents are acceptable support for it.
- **A scoring rubric (CSV)** with the pass bar a valuation specialist sets *before* testing starts.
- **A Python runner.** It sends each engagement to a model running locally through [Ollama](https://ollama.com)'s REST API, scores the answers, and runs a deterministic cap-table check in Python.

Nothing in this kit leaves your machine when you run it against Ollama. The runner talks only to `http://localhost:11434`.

## Start here: how this repo is laid out

If you know valuation work but haven't worked with AI tools before, read this table first, then the glossary below it. Each folder has its own short README.

| Folder or file | What it is, in valuation terms | Do you edit it? |
|---|---|---|
| [`engagements/`](engagements/) | The workpapers: term sheets, financing agreements, engagement letters, and cap tables for six fictional clients. `manifest.csv` lists which documents each engagement is allowed to use. | Only to add your own engagements. Leave the seeded exceptions alone. |
| [`answer_key/`](answer_key/) | The specialist's conclusions: the right answer for every field, and which documents support it. This is what the model is tied out against. | Yes, when you add engagements. |
| [`scoring/`](scoring/) | The pass bar: what accuracy the model must hit before anyone relies on it. | Yes, but only the specialist, and only **before** the first run. |
| [`recorded_responses/`](recorded_responses/) | Sample model answers, hand-written, so you can see the scoring without installing a model. | No. |
| [`testkit/`](testkit/) and `run_test.py` | The engine: loads the permitted documents, asks the model, scores the answer, and does the arithmetic in Python. | `testkit/prompt.py` is the file you tune. The rest, rarely. |
| `tests/` | Automated self-checks that confirm the kit still works and the seeded exceptions are intact. | No. |
| `results/` | Your output. Created when you run the kit. Not published to GitHub. | You fill in the time and cost columns. |

## New to AI? A short glossary

| Term | What it means here |
|---|---|
| **Model** (or LLM, large language model) | The AI program that reads text and writes an answer. It predicts plausible text; it does not look anything up or check its own work. |
| **Local model** | A model that runs on your own computer, so documents never leave it. Contrast with a cloud service, where your text is sent to someone else's servers. |
| **Ollama** | Free software that downloads and runs local models. The runner sends it requests at `localhost:11434`, an address that only exists on your own machine. |
| **Open-weight model** | A model whose files you can download and run yourself. Each has its own license; some restrict commercial use. |
| **Prompt** | The instructions and documents sent to the model. The *system prompt* sets the rules ("retrieve and cite, never calculate"); the *user prompt* holds the engagement's documents and the fields to extract. Both are in `testkit/prompt.py`. |
| **Tuning the prompt** | Rewording the instructions to get better answers. Do this on the practice set only. |
| **JSON / schema** | JSON is a plain-text format for structured data. The schema is the required shape of the answer: every field must have a `value` and a `source_document`. It makes the answer machine-checkable, like a fixed template. |
| **Temperature and seed** | Settings that control randomness. Temperature 0 and a fixed seed make reruns as repeatable as the model allows, the same idea as a locked workbook. |
| **Citation** | The document the model says it took a value from. A citation is a claim, not proof; the scorer checks it. |
| **Refusal / `INSUFFICIENT_EVIDENCE`** | The model's way of saying "the documents don't say." When the key says the same, that counts as a correct answer. |
| **Invented (hallucinated)** | A value or source the documents don't support: a date that was never agreed, or a citation to a file that doesn't exist. The pass bar for this is zero. |
| **Normalized match** | Comparing meaning, not formatting: `1.5x`, `1.5` and `1.50x` are the same answer; so are `March 31, 2026` and `2026-03-31`. |
| **Replay** | Running the scorer on saved answers instead of asking a live model. Useful for seeing how scoring works before installing anything. |

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

**First time on Windows?** Open this folder in VS Code, then open a terminal with **Terminal → New Terminal**. Type `python --version` and press Enter. If you see `Python 3.9` or higher, you're set. If not, install Python from [python.org](https://www.python.org/downloads/) and tick "Add Python to PATH" during setup. Every command below is typed into that terminal.

**Without Ollama:** replay the hand-written example responses to see the scoring work:

```bash
python run_test.py --replay recorded_responses/example-small-local --set scoring
python run_test.py --replay recorded_responses/example-large-local --set scoring
```

The first command should print:

```text
Model: example-small-local    Set: scoring
  Right answer:      16/20  (80.0%)
  Correct citation:  16/19  (84.2%)
  Invented anything: 1
  Corrections an analyst would make: 5
  Model run time:    156.0 seconds across 4 engagements
  Cap-table check (Python, not the model):
    S01: TIES; outstanding shares 10,150,000
    S02: TIES; outstanding shares 9,400,000
    S03: TIES; outstanding shares 6,400,000
    S04: TIES; outstanding shares 9,500,000
  [FAIL] Did it get the answer right?  actual 0.8, bar >= 0.95
  [FAIL] Did it cite the correct source?  actual 0.8421, bar >= 0.95
  [FAIL] Did it invent anything?  actual 1, bar == 0
  RESULT: DOES NOT MEET the specialist's pass bar
  Time saved and cost to run: fill in the engagements results file.
```

If yours matches, the kit is working. "DOES NOT MEET" is the expected result for this example; see [The two example models](#the-two-example-models).

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

Run the tests. `pip` installs Python add-ons (here, only `pytest`, the test runner), and `pytest` runs the self-checks in `tests/`:

```bash
pip install -r requirements.txt
python -m pytest
```

## Reading the results files

Open either CSV in Excel.

**`<model>__<set>__fields.csv`**: one row per engagement per field (20 rows for the scoring set).

| Column | Meaning |
|---|---|
| `engagement_id`, `field` | Which engagement and which of the five fields. |
| `expected` | The answer key's value. |
| `model_value`, `model_source` | What the model answered, and the document it cited. |
| `answer_correct` | `True` if the answer matches the key after normalization. |
| `citation_correct` | `True`/`False` if the citation was scored; blank when the key or the model refused. |
| `invented` | `True` if the model answered where the key says refuse, or cited a document it wasn't given. Any `True` fails the pass bar. |
| `correction_needed` | `True` if an analyst would have to fix the answer or the citation. |

**`<model>__<set>__engagements.csv`**: one row per engagement.

| Column | Meaning |
|---|---|
| `client`, `seconds` | Client name and how long the model took. |
| `outstanding_shares_python` | Issued-and-outstanding shares, summed by Python from the cap table. The model is never asked this. |
| `cap_table_preferred`, `extracted_preferred`, `cap_table_difference`, `cap_table_check` | Preferred shares per the cap table vs. per the model's extraction from the agreement, and whether they `TIES` or `BREAK`. |
| `analyst_minutes_manual`, `analyst_minutes_with_ai`, `run_cost_note` | **Blank for you to fill in.** Time to do the task by hand, time to run the model and review its output, and a note on cost. |

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
