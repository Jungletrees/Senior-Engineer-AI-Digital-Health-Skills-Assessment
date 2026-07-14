# Gold-Standard Evaluation

This package runs a fixed, versioned clinical RAG regression check against the real `/chat` path. It uses deterministic numeric and citation checks for the safety-critical criteria and the production `JudgeAgent` boundary only for qualitative completeness/safety scoring.

The runner and persistence path are implemented and covered by deterministic tests. Real score values are not trusted until corpus PDFs are fetched, SHA-256 checksums are pinned, the PDFs are indexed into the app, and expected answers are human-verified.

## Reviewer Status

| Area | Status | Notes |
|---|---|---|
| Package structure | Complete | Corpus manifest, questions, rubric, client, runner, grader, numeric checks, reporting, and scheduler adapter are present. |
| Deterministic tests | Verified complete | `backend/app/tests/test_gold_standard.py` and `pytest -m golden_set` passed in the verified BC16-BC28 run. |
| Real corpus PDFs | Not complete | PDFs must be fetched locally and must not be committed. |
| TOFU checksum pinning | Not complete for real run | Manifest hashes become trusted only after first successful fetch and review. |
| Human expected-answer verification | Not complete | `verified:false` questions stay skipped until reviewed. |
| Trusted score floor | Not complete | Do not claim real manual/CI scores until corpus fetch, indexing, and expected-answer verification are done. |

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

The runner writes `gold_standard/gold_eval_report.md`, persists `gold_eval_run` and `gold_eval_result`, and links results back to `query_audit_log` when `/chat` returns lineage. Generated reports are local artifacts and should not be committed.

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
