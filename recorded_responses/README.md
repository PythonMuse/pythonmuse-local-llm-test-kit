# recorded_responses/

Saved model answers, so you can see the scoring work without installing Ollama or a model.

**These are hand-written and illustrative. They are not output from any real model.** The folder names `example-small-local` and `example-large-local` are labels, not products. Each was written to show a particular failure; see [The two example models](../README.md#the-two-example-models) in the main README.

## How they're used

```bash
python run_test.py --replay recorded_responses/example-small-local --set scoring
```

`--replay` tells the runner to read `S01.json`, `S02.json`, and so on from the folder instead of asking a live model. Everything after that (scoring, cap-table check, pass bar) runs exactly as it would for a live model. The automated tests use these files too, so don't edit them.

## What's in each file

Each file is shaped like a real response from Ollama:

- `model`: the label.
- `message.content`: the model's answer, as JSON text, one entry per field with a `value` and a `source_document`.
- `total_duration`: how long the model took, in nanoseconds (38,400,000,000 = 38.4 seconds).

## Saving your own

To keep a live model's answers for later review, make a new folder here with one `<engagement_id>.json` per engagement in the same shape, then replay it. Don't save answers built on real client documents in this public repository.
