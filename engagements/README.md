# engagements/

The workpapers. Each subfolder is one fictional engagement, and every company, person, and figure in it is made up.

## What's in each engagement folder

| File | What it is | Why it matters to the test |
|---|---|---|
| `term_sheet.md` | The non-binding summary of deal terms. | Often right, but not authoritative. Where it disagrees with the agreement, the agreement governs. |
| `financing_agreement.md` | The executed charter and stock purchase agreement. | The governing source for preference, participation, conversion, and shares issued. |
| `engagement_letter.md` | The letter engaging the valuation firm. | The only source for the valuation date. |
| `cap_table.csv` | Shares outstanding by class. | Python, not the model, sums it and checks it against the agreement. |

## Practice and scoring

- `practice/` (P01–P02): tune the prompt here as often as you like.
- `scoring/` (S01–S04): score here, and only here. Don't tune against these.

## `manifest.csv` is the permission list

A document reaches the model only if `manifest.csv` lists it for that engagement. Being saved in the folder is not permission. That's why `S01-brightwater-analytics/` holds a misfiled term sheet from another client, and why the model never sees it.

Columns: `engagement_id`, `set` (practice or scoring), `client`, `series_name` (the preferred series being valued; must match the cap table row), `document_id` (the name the model must cite), `path`.

## Do not "fix" the sample data

The scoring engagements contain deliberate traps: the misfiled Harrowgate Foods term sheet in S01, the 1x vs 1.5x conflict in S02, the unagreed valuation date in S03, and the stale cap table in S04. They are the point of the test, and `tests/test_kit.py` checks that they're still there. See [The seeded exceptions](../README.md#the-seeded-exceptions) in the main README.

## Adding your own engagements

1. Create a folder under `practice/` or `scoring/`, using material approved for the test (redacted or synthesized).
2. Add one row per document to `manifest.csv`.
3. Add the specialist's answers to [`../answer_key/answer_key.csv`](../answer_key/).
