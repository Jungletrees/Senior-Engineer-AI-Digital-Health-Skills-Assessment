# Gold-Standard Evaluation

This package runs a fixed, versioned clinical RAG regression check against the real `/chat` path. It uses deterministic numeric and citation checks for the safety-critical criteria and the production `JudgeAgent` boundary only for qualitative completeness/safety scoring.

## One-Time Corpus Setup

```bash
python -m gold_standard.fetch_corpus
```

The first successful run pins SHA-256 values into `gold_standard/corpus/corpus_manifest.yaml`. Commit the manifest change, but never commit PDFs from `gold_standard/corpus/files/`.

Before trusting a score, verify each expected answer against the source:

```bash
python -m gold_standard.verify_expected --search
```

Questions with `verified: false` are skipped by the runner.

## Manual Runs

```bash
python -m gold_standard.runner --trigger manual --sample 8
python -m gold_standard.runner --trigger ci --floor 85
```

The runner writes `gold_standard/gold_eval_report.md`, persists `gold_eval_run` and `gold_eval_result`, and links results back to `query_audit_log` when `/chat` returns lineage.

## Runtime Settings

Use `.env.example` as the source of truth for production variables. The most relevant settings are:

- `GOLD_CHAT_URL`: backend `/chat` endpoint.
- `GOLD_CHAT_AUTH`: optional bearer or service token.
- `GOLD_EVAL_CONCURRENCY`: bounded parallel `/chat` calls.
- `GOLD_EVAL_JUDGE_MODEL`: optional override; defaults to `JUDGE_MODEL`.
- `GOLD_EVAL_CRON`: scheduled run cadence.
- `GOLD_EVAL_DEVIATION_ABS_DROP` and `GOLD_EVAL_DEVIATION_ZSCORE`: alert thresholds.

## Scheduling

The preferred path is the backend scheduler with `ENABLE_SCHEDULED_JOBS=true`; it runs under the Postgres advisory-lock singleton guard. Teams that avoid in-process scheduling can use `crontab.example` or the systemd examples in this directory.
