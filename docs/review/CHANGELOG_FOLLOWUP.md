# Changelog (Follow-up)

- Added streaming iterators for Azure OpenAI and Bedrock adapters with env toggle (`FMF_EXPERIMENTAL_STREAMING`).
- Introduced deterministic ID + provenance layer (`fmf.core.ids`), updating loaders/chunkers and adding reproducibility tests.
- Hardened Local/S3/SharePoint connectors to share `BaseConnector`, include retries, and return managed streams.
- Implemented provider registry with decorator-based registration; `build_llM_client` now honours registered factories.
- Enhanced S3 exporter for atomic overwrite semantics and documented unsupported upsert path.
- BaseProvider streaming now emits `TokenChunk` instances so metadata can propagate alongside tokens without breaking callbacks.
- Document/Chunk IDs incorporate content length and MIME metadata; loaders persist a manifest for run idempotency.
- Normalised error hierarchy under `fmf.core.errors` and replaced local `datetime.utcnow()` calls with timezone-aware variants.
- Expanded `fmf keys test` to emit diagnostics for connectors/providers/exporters while preserving secret redaction.
- CLI gains `--quiet`/`--json` parity across commands and maps framework errors to deterministic exit codes.
- Refreshed `scripts/analyse_csv.py`, `scripts/images_multi.py`, and `scripts/text_to_json.py` to stay
  recipe-first with shared `--recipe/--config` flags while delegating summaries to the SDK/CLI helper.
- CI now runs lint (ruff), type-check (mypy), pytest, and coverage (≥70%) across Python 3.11/3.12; added `ruff.toml` and `mypy.ini`.
- Added runnable recipe scripts for streaming, deterministic IDs, and export write modes.
