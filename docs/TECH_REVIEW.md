# FMF Technical Review — Findings and Recommendations

Audience: maintainers and contributors. This is a principled review of the codebase after the V3 UX pass, highlighting duplicates, unused/incomplete code, gaps, and near‑term improvements.

## Summary

The core layering (connectors, processing, inference adapters, chain runner, exporters) is solid and extensible. The new SDK + CLI wrappers + Recipe YAMLs make common workflows much easier. Key areas to tighten now: reduce duplication in the runner, normalize glob patterns, complete multimodal JSON enforcement and grouping ergonomics, and address small DX/observability gaps.

## Duplicates, Unused, and Incomplete

- Runner duplication (minor)
  - `run_chain_config` serializes to a temp YAML and calls `run_chain`, which then delegates to `_run_chain_loaded`. This is fine for now, but we could remove the temp write by invoking `_run_chain_loaded` directly with a constructed `ChainConfig` to avoid file I/O.
  - The runner contains repeated dict-vs-model access patterns (e.g., `getattr(x, ...) if not dict else x.get(...)`). Consider a small helper (e.g., `cfg_get(obj, key, default)`) to centralize this.

- Unused imports and helpers
  - `ensure_dir` is imported in the runner but not used in some paths.
  - Review for any other unused imports across modules; static analysis (ruff) can catch these.

- Incomplete exporters (as declared by design)
  - `sharepoint_excel`, `redshift`, `delta`, `fabric_delta` remain stubs. We call this out clearly but should guard their code paths with friendly errors and documentation links.

- Pydantic warning: `RedshiftSink.schema`
  - Warning: "Field name 'schema' in 'RedshiftSink' shadows an attribute in parent 'BaseModel'". Rename to `db_schema` (and update references) to eliminate noise.

- Tests creating tracked artefacts
  - Some tests resulted in real artefacts being added to git (e.g., `artefacts/...`). Ensure `.gitignore` excludes `artefacts/` and tests always use temp dirs (they generally do), and avoid committing artefacts.

## Logic Gaps and Edge Cases

- Glob patterns with brace expansion
  - We introduced selects like `"**/*.{md,txt,html}"`. Python `fnmatch` doesn’t support brace expansion, so these won’t match. This can silently cause empty inputs.
  - Fix: expand braces at parse time or accept lists (SDK can split into explicit patterns). E.g., `['**/*.md', '**/*.txt', '**/*.html']`.

- Multimodal JSON enforcement and grouping
  - JSON enforcement is implemented in row/chunk paths, but the `images_group` branch returns `comp.text` directly. To be consistent, apply the same enforcement when `step.output_expects=json`.
  - Add group‑level metadata (e.g., list of source_uris) into outputs for easier downstream attribution.
  - Consider group size limits and image count caps based on provider limits; log when oversized groups are truncated.

- Image payload sizing
  - We embed images as base64 data URLs. This is straightforward, but can explode request size. Consider optional downsampling or size caps, and warn when exceeding a threshold.

- Connector auto‑selection (SDK)
  - `_auto_connector_name()` falls back to `'local_docs'` even if not configured. Better: if no connectors are configured, auto‑generate a minimal local connector or error with a clear message directing the user.

- Chain outputs vs. sink types
  - `run_chain` saves outputs to local files, and `export` in chain relies on exporter capabilities where bytes are passed. Some sinks (e.g., DynamoDB) require iterable dicts. We added CLI export parsing for such sinks, but chain outputs don’t yet adapt automatically by sink type.
  - Improvement: detect sink type in chain outputs stage and convert bytes→records when needed (or standardize on jsonl files + a `records_from_path` mode for record sinks).

- Error handling and visibility
  - JSON repair failures are recorded in metrics but not surfaced to the user beyond artefacts. Consider summarized warning logs with step IDs and failure counts.
  - The `DeprecationWarning` for `datetime.utcnow()` spams tests. Switch to timezone‑aware `datetime.now(datetime.UTC)`.

- Rate limiting and concurrency
  - Basic `RateLimiter` is provider‑agnostic; consider per‑provider defaults and configurability via YAML (e.g., tokens per second for Anthropic vs. Azure OpenAI).
  - Add a maximum concurrent requests option per step in chain (already a `concurrency` at the chain level).

- Observability
  - Add run_id and step_id context to logs by default. The JSON logs are good, but standardizing keys across modules would help (logger adapter or contextvars).
  - Add spans around export operations and connector listing to improve E2E traces.

- SDK return_records ergonomics
  - SDK reads saved JSONL to return records; this is fine but could offer a `return_path=True` to avoid reading and let caller choose. Also consider a consistent return shape ({paths, records?}).

- CLI `doctor`
  - Currently prints provider and first connector. Extend to validate presence of required env vars for the selected provider, and list visible files for quick sanity checks.

## Missing or Nice‑to‑Have Features

- Recipe YAML: validation and schema
  - Define and validate recipe schemas (pydantic model or JSON Schema) for `csv_analyse`, `text_files`, `images_analyse` so we can give immediate feedback on invalid fields.

- Quickstart wizard
  - Interactive `fmf quickstart` to generate recipe YAMLs or SDK snippets for CSV/Text/Images with minimal Q&A.

- ChainBuilder (typed)
  - Implement the builder to eliminate remaining dict composition in SDK internals. Recipes → ChainBuilder → chain runner keeps one orchestration path.

- Exporters
  - Implement `sharepoint_excel` upsert (even a basic version), and clear error messages for `redshift`/`delta`/`fabric` stubs.
  - Optional local CSV exporter (append/upsert) for teams that want in‑place updates (we intentionally avoided this in favor of separate outputs, but demand may arise).

- Enhanced multimodal
  - Optional image deduplication by hash in groups.
  - Optional image captions per item before group aggregation.

- End‑to‑end examples
  - Add recipe‑first examples for all workflows; ensure README and USAGE emphasize Recipes + SDK/CLI.

## Concrete Fix List (Short‑Term)

1) Glob normalization: replace brace patterns with explicit lists in defaults (SDK + examples) or implement brace expansion.
2) Apply JSON enforcement in `images_group` when step expects JSON; update tests accordingly.
3) Rename `RedshiftSink.schema` → `db_schema` to remove pydantic warning.
4) Switch to `datetime.now(datetime.UTC)` in runner to remove deprecation noise.
5) Add `.gitignore` rule for `artefacts/` to avoid contamination from tests.
6) Unify config access pattern with a helper to reduce duplication and errors.
7) Improve `doctor` to check provider env vars and report missing credentials.
8) Document image payload size guidance; consider optional resizing or max images per group default.

## Longer‑Term Improvements

- ChainBuilder + Recipe validation: firm up the typed interfaces and error messages around recipes.
- Sink‑aware chain exporting: automatically convert outputs to records for record sinks within chain runs.
- Observability: structured, consistent log payloads with run_id/step_id; add spans for export/connector ops.
- Provider‑specific rate limits: configurable through YAML profiles.

## Closing

The project now provides strong foundations and a much smoother developer experience (SDK/CLI/Recipes). Tackling the above short‑term fixes will further improve reliability and clarity. The longer‑term items (builder, validation, sink‑aware exports, observability) will harden the orchestration layer without altering the pluggable core.

