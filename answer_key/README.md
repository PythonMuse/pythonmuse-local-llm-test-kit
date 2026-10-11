# answer_key/

What the specialist actually concluded, field by field. The model's answers are tied out against this file, the same way you'd tie a schedule to support.

`answer_key.csv` has one row per engagement per field: five fields × six engagements = 30 rows.

| Column | Meaning |
|---|---|
| `engagement_id`, `set` | Which engagement, and whether it's practice or scoring. |
| `field` | One of the five fields: `liq_pref_multiple`, `participation`, `conversion_ratio`, `valuation_date`, `preferred_shares_issued`. |
| `expected_value` | The right answer. `INSUFFICIENT_EVIDENCE` means the documents don't support any answer, and the model should refuse. |
| `acceptable_sources` | Documents the model may cite for this answer, separated by `\|`. Blank when the right answer is a refusal. |
| `source_section` | Where in the document the answer is, for the reviewer. Not scored. |
| `note` | Context. Rows starting `SEEDED:` mark the deliberate traps. |

## Who writes it

The valuation specialist, from the work as it was actually concluded, and before any model is run. If the person tuning the prompt also writes the key, the test isn't independent.

## Formatting

You don't need to match the model's formatting. The scorer normalizes both sides, so `1x`, `1`, and `1.0x` all match. Participation uses `non-participating`, `participating`, or `participating-capped`. Ratios are written preferred:common (`1:1.25` means one preferred share converts into 1.25 common shares).
