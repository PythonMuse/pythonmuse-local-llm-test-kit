# scoring/

The pass bar. `scoring_rubric.csv` defines what the model must achieve on the scoring set before anyone relies on it.

| Column | Meaning |
|---|---|
| `criterion_id` | Internal name the runner uses. Don't rename these. |
| `criterion` | The question in plain English, e.g. "Did it invent anything?" |
| `how_scored` | Exactly how it's measured. |
| `pass_bar` | The threshold (see below). |
| `set_by` | Who owns the number: the valuation specialist or the reviewer. |

## Pass-bar syntax

- `>= 0.95` means at least 95%.
- `== 0` means exactly zero. Used for invented answers: one invention fails the run.
- `recorded` means the runner doesn't evaluate it. A person records it in the results file (corrections, minutes saved, cost to run).

The runner checks the pass bar on the **scoring set only**. A practice run reports the numbers but never says pass or fail.

## Set it before the first run

The values here are examples. In a real test, the valuation specialist sets them before testing starts and doesn't move them afterward. Lowering the bar after seeing the results is the same as changing the materiality threshold after finding the misstatement.
