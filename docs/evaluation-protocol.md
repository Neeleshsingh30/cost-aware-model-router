# Evaluation protocol

## Dataset separation

`data/test_dataset.json` is the held-out assessment set. It contains 40 cases: 10 each for classification, extraction, summarisation, and question answering. The evaluator checks the count, task balance, required fields, supported task types, and unique case IDs before making provider calls.

Do not use these cases or their expected answers to tune prompts, thresholds, or routing rules. Keep any development and prompt-tuning examples in a separate `data/dev_dataset.json`; that development file is not currently part of this repository. The repository history identifies the test set as an existing project artifact but does not establish whether it was used for tuning before this protocol was added. Treat results as strictly held-out only if that separation is observed in practice.

Every evaluation summary records the test file's SHA-256 hash, run time, model IDs, routing thresholds, and configured prices. This makes it possible to identify exactly which dataset and configuration produced the CSV.

## Scoring

- **Classification:** exact match after trimming, lowercasing, and whitespace normalization. A semantically equivalent but differently named category does not count as correct.
- **Extraction:** normalized recursive value matching for each expected field. The score is the matched expected fields divided by the larger of expected and returned top-level field counts, so missing or extra top-level fields reduce the score. A score of 1.0 is required for `correct=true`.
- **Summarisation and Q&A:** deterministic token-level F1 after lowercasing and tokenization. The score is lexical overlap, not semantic equivalence or factuality; `correct=true` uses the evaluator's 0.5 F1 threshold.

The CSV's `accuracy` field is the mean score over successful cases; for extraction and text-generation tasks it can be fractional. Failed cases are reported separately and excluded from the mean score. Costs remain unavailable if any case lacks token usage or configured pricing; they are never silently counted as zero. The router strategy's reported model calls include both the initial and final model when it escalates.

## Outputs and run cost

Run `python -m backend.app.evaluation.evaluator` from the repository root. It performs a fast-only baseline call, a strong-only baseline call, and a router run for each held-out case. Each router run starts with the fast model and can add a strong-model call if it escalates. Therefore a full 40-case run makes at least 120 and up to 160 provider calls, and may incur charges. The saved 2026-10-15 run made 129 calls (9 router escalations).

- `data/evaluation_results.csv` contains overall and per-task strategy summaries plus run configuration and dataset hash.
- `data/evaluation_cases.csv` contains each case's score, status, model calls, usage, cost, and error.

Do not treat an older results CSV as final unless its dataset hash, run configuration, and provenance are available and verified.
