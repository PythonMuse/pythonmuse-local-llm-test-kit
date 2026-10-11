# testkit/

The engine. `run_test.py` in the main folder calls these five files in order for each engagement:

```text
retrieval.py  ->  prompt.py  ->  ollama_client.py  ->  scoring.py  ->  deterministic.py
 (who may see     (what the       (asks the model,     (ties out to      (Python does
  what)            model is told)  or replays)          the answer key)   the arithmetic)
```

| File | What it does, in plain English |
|---|---|
| `retrieval.py` | The permission filter. Loads only the documents `manifest.csv` lists for the engagement, and stops the run if an engagement mixes clients or folders. Access is decided before the model sees anything. |
| `prompt.py` | The instructions sent to the model: its role ("retrieve and cite, never calculate"), the rules, the five fields, and the required answer format. **This is the file you tune.** |
| `ollama_client.py` | Sends the prompt to the local model through Ollama and gets the answer back, or reads a saved answer when you use `--replay`. Sets temperature 0 and a fixed seed so reruns are repeatable. |
| `scoring.py` | Reads the model's answer, normalizes formats, compares each field to the answer key, and flags wrong answers, wrong citations, and inventions. Then checks the totals against the pass bar. |
| `deterministic.py` | The calculator. Sums outstanding shares from the cap table and compares the cap table's preferred shares with what the model extracted from the agreement (TIES or BREAK). |

## If you want to change something

| You want to... | Edit |
|---|---|
| Reword the instructions to the model | `prompt.py` (`SYSTEM_PROMPT` and `FIELD_DESCRIPTIONS`). Tune on practice only. |
| Extract a different field | `prompt.py` (`FIELDS`), a normalizer in `scoring.py`, and new rows in the answer key. |
| Accept a new date or number format | The normalizers at the top of `scoring.py`. |
| Change the pass bar | Not here: [`../scoring/scoring_rubric.csv`](../scoring/), and only the specialist. |
| Use a different Ollama address | Not here: `python run_test.py --host <address>`. |

After any change, run `python -m pytest` from the main folder. If a test fails, the change broke something the kit depends on.
