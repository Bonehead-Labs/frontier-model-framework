# Changelog

## [0.2.0] - 2025-09-21
- Refactored `chain.runner` into helper stages to simplify future pipeline work with no behaviour changes.
- Emitted retry metrics (`retry.attempts`, `retry.failures`, `retry.success`, `retry.sleep_seconds`) and documented observability knobs.
- Added CI security and quality gates (pip-audit, bandit, radon, jscpd) with reusable scripts.
- Increased coverage for tracing, table-row processing, and SDK orchestrators with new targeted unit tests.

## [0.1.0]
- Initial release.
