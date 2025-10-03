# Prompt Store Abstraction

FMF treats prompts as text inputs to inference.  
Where those prompts *come from* is abstracted behind a `PromptStore` interface.

## Backends

- **Local Store**  
  Prompts live in the repo (`/prompts/<name>/<version>.prompt.txt`) with optional alias maps (`aliases.json`).  
  Good for development and offline use.

- **MLflow Store**  
  Prompts are registered in the **MLflow Prompt Registry** and loaded at runtime via alias or version (`prompts:/<name>@<alias>`).  
  Requires an MLflow tracking/registry server. Provides:
  - Immutable prompt versions
  - Aliases (`production`, `staging`, etc.)
  - Metadata/tags and search
  - Auditability and lineage

## Usage Pattern

1. **Configure** which backend to use in `fmf.yaml`:
   ```yaml
   prompts:
     backend: local    # or "mlflow"
     root: ./prompts   # used by local
     tracking_uri: http://mlflow:5000  # used by mlflow
     default_selector: production
Here’s a very high-level snippet you can drop into FMF’s repo docs (e.g. `docs/architecture/prompts.md` or top of the `prompt_store` package):


# Prompt Store Abstraction

FMF treats prompts as text inputs to inference.  
Where those prompts *come from* is abstracted behind a `PromptStore` interface.

## Backends

- **Local Store**  
  Prompts live in the repo (`/prompts/<name>/<version>.prompt.txt`) with optional alias maps (`aliases.json`).  
  Good for development and offline use.

- **MLflow Store**  
  Prompts are registered in the **MLflow Prompt Registry** and loaded at runtime via alias or version (`prompts:/<name>@<alias>`).  
  Requires an MLflow tracking/registry server. Provides:
  - Immutable prompt versions
  - Aliases (`production`, `staging`, etc.)
  - Metadata/tags and search
  - Auditability and lineage

## Usage Pattern

1. **Configure** which backend to use in `fmf.yaml`:
   ```yaml
   prompts:
     backend: local    # or "mlflow"
     root: ./prompts   # used by local
     tracking_uri: http://mlflow:5000  # used by mlflow
     default_selector: production


2. **Get & format** a prompt:

   ```python
   store = make_store(cfg)
   template, ver = store.get("invoice_summary", cfg.prompts.default_selector)
   text = store.format(template, data=summary)
   ```

3. **Send** the formatted text into any FMF inference point (AzureOpenAI, Bedrock, etc.).

## Migration Path

* Start with **local store** (works immediately).
* When an MLflow server is available, switch `backend: mlflow` with no code changes.
* Optionally, use MLflow’s `register_prompt` and `set_alias` via FMF CLI to promote versions.

---

This lets FMF apps stay provider-agnostic: inference always receives plain text prompts, while prompt versioning and audit can be layered in later via MLflow.


