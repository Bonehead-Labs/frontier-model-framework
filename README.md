Frontier Model Framework (FMF)
==============================

This repository implements a pluggable framework for working with frontier LLMs (Azure OpenAI, AWS Bedrock, and more). Refer to AGENTS.md for the overall architecture and conventions, and to BUILD_PLAN.md for the prioritized build plan and milestone progress.

Quick Start
-----------

1. Copy `examples/fmf.example.yaml` to `fmf.yaml` and adjust endpoints/keys.
2. Place sample Markdown files under `./data`.
3. Register the example prompt (optional, registry auto-registers on chain run):
   `fmf prompt register examples/prompts/summarize.yaml#v1`
4. Process data locally:
   `fmf process --connector local_docs --select "**/*.md" -c fmf.yaml`
5. Run the sample chain and (optionally) export:
   `fmf run --chain examples/chains/sample.yaml -c fmf.yaml`

Documentation
-------------

- Architecture and conventions: `AGENTS.md`
- Build plan and milestone tracking: `BUILD_PLAN.md`
- Deployment notes and IAM examples: `docs/DEPLOYMENT.md`, `docs/IAM_POLICIES.md`
- Examples: `examples/`

