from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ..chain.runner import run_chain_config
from ..config.loader import load_config
import yaml as _yaml


class FMF:
    def __init__(self, *, config_path: Optional[str] = None) -> None:
        self._config_path = config_path or "fmf.yaml"
        self._cfg = None
        try:
            self._cfg = load_config(self._config_path)
        except Exception:
            self._cfg = None

    @classmethod
    def from_env(cls, config_path: str | None = None) -> "FMF":
        # If not provided, prefer fmf.yaml in CWD; otherwise allow SDK to run with minimal assumptions
        if config_path is None and os.path.exists("fmf.yaml"):
            config_path = "fmf.yaml"
        return cls(config_path=config_path)

    # --- CSV per-row analysis ---
    def csv_analyse(
        self,
        *,
        input: str,
        text_col: str,
        id_col: str,
        prompt: str,
        save_csv: str | None = None,
        save_jsonl: str | None = None,
        expects_json: bool = True,
        parse_retries: int = 1,
        return_records: bool = False,
        connector: str | None = None,
        rag_options: Dict[str, Any] | None = None,
    ) -> Optional[List[Dict[str, Any]]]:
        filename = os.path.basename(input)
        c = connector or self._auto_connector_name()
        save_csv = save_csv or "artefacts/${run_id}/analysis.csv"
        save_jsonl = save_jsonl or "artefacts/${run_id}/analysis.jsonl"

        output_block: Any = "analysed"
        if expects_json:
            output_block = {
                "name": "analysed",
                "expects": "json",
                "parse_retries": parse_retries,
                "schema": {"type": "object", "required": ["id", "analysed"]},
            }

        rag_cfg = _build_rag_block(rag_options, default_text_var="rag_context", default_image_var="rag_images")

        chain = {
            "name": "csv-analyse",
            "inputs": {
                "connector": c,
                "select": [filename],
                "mode": "table_rows",
                "table": {"text_column": text_col, "pass_through": [id_col]},
            },
            "steps": [
                {
                    "id": "analyse",
                    "prompt": (
                        "inline: Return a JSON object with fields 'id' and 'analysed'.\n"
                        "Only output valid JSON, nothing else.\n\n"
                        "ID: {{ id }}\n"
                        "Comment:\n{{ text }}\n"
                    ),
                    "inputs": {"id": f"${{row.{id_col}}}", "text": "${row.text}"},
                    "output": output_block,
                    **({"rag": rag_cfg} if rag_cfg else {}),
                }
            ],
            "outputs": [
                {"save": save_jsonl, "from": "analysed", "as": "jsonl"},
                {"save": save_csv, "from": "analysed", "as": "csv"},
            ],
            "concurrency": 4,
            "continue_on_error": True,
        }

        res = run_chain_config(chain, fmf_config_path=self._config_path or "fmf.yaml")
        if not return_records:
            return None
        # Load records from saved analysis JSONL
        out_path = save_jsonl.replace("${run_id}", res.get("run_id", ""))
        try:
            return list(_read_jsonl(out_path))
        except Exception:
            # Fallback to last outputs.jsonl if save path unknown
            run_dir = res.get("run_dir")
            if run_dir:
                return list(_read_jsonl(os.path.join(run_dir, "outputs.jsonl")))
            return None

    def text_files(
        self,
        *,
        prompt: str,
        connector: str | None = None,
        select: List[str] | None = None,
        save_jsonl: str | None = None,
        expects_json: bool = True,
        return_records: bool = False,
        rag_options: Dict[str, Any] | None = None,
    ) -> Optional[List[Dict[str, Any]]]:
        c = connector or self._auto_connector_name()
        save_jsonl = save_jsonl or "artefacts/${run_id}/text_outputs.jsonl"
        chain = _build_text_chain(
            connector=c,
            select=select,
            prompt=prompt,
            save_jsonl=save_jsonl,
            expects_json=expects_json,
            rag_options=rag_options,
        )
        res = run_chain_config(chain, fmf_config_path=self._config_path or "fmf.yaml")
        if not return_records:
            return None
        out_path = save_jsonl.replace("${run_id}", res.get("run_id", ""))
        return list(_read_jsonl(out_path))

    def images_analyse(
        self,
        *,
        prompt: str,
        connector: str | None = None,
        select: List[str] | None = None,
        save_jsonl: str | None = None,
        expects_json: bool = True,
        group_size: int | None = None,
        return_records: bool = False,
        rag_options: Dict[str, Any] | None = None,
    ) -> Optional[List[Dict[str, Any]]]:
        c = connector or self._auto_connector_name()
        save_jsonl = save_jsonl or "artefacts/${run_id}/image_outputs.jsonl"
        if group_size and group_size > 1:
            chain = _build_images_group_chain(
                connector=c,
                select=select,
                prompt=prompt,
                save_jsonl=save_jsonl,
                expects_json=expects_json,
                group_size=group_size,
                rag_options=rag_options,
            )
        else:
            chain = _build_images_chain(
                connector=c,
                select=select,
                prompt=prompt,
                save_jsonl=save_jsonl,
                expects_json=expects_json,
                rag_options=rag_options,
            )
        res = run_chain_config(chain, fmf_config_path=self._config_path or "fmf.yaml")
        if not return_records:
            return None
        out_path = save_jsonl.replace("${run_id}", res.get("run_id", ""))
        return list(_read_jsonl(out_path))

    # --- Recipe runner ---
    def run_recipe(
        self,
        path: str,
        *,
        rag_pipeline: str | None = None,
        rag_top_k_text: int | None = None,
        rag_top_k_images: int | None = None,
        use_recipe_rag: bool | None = None,
    ) -> dict:
        """Run a high-level recipe YAML (csv_analyse | text_files | images_analyse).

        The recipe file is a minimal schema, e.g.:
          recipe: csv_analyse
          input: ./data/comments.csv
          id_col: ID
          text_col: Comment
          prompt: Summarise this comment
          save: { csv: artefacts/${run_id}/analysis.csv, jsonl: artefacts/${run_id}/analysis.jsonl }
        Optional RAG support can be declared in the recipe under `rag:` and toggled via
        `use_recipe_rag` or overridden with the explicit rag_* parameters.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = _yaml.safe_load(f) or {}
        rtype = (data.get("recipe") or "").strip()
        raw_rag_cfg = data.get("rag")
        rag_cfg = raw_rag_cfg if isinstance(raw_rag_cfg, dict) else {}

        rag_options: Dict[str, Any] | None = None
        if rag_pipeline:
            rag_options = dict(rag_cfg or {})
            rag_options["pipeline"] = rag_pipeline
        else:
            pipeline_name = rag_cfg.get("pipeline")
            want_recipe = True if use_recipe_rag is None else bool(use_recipe_rag)
            if pipeline_name and want_recipe:
                rag_options = dict(rag_cfg)

        if rag_options:
            if rag_top_k_text is not None:
                rag_options["top_k_text"] = rag_top_k_text
            if rag_top_k_images is not None:
                rag_options["top_k_images"] = rag_top_k_images

        if rtype == "csv_analyse":
            return {
                "result": self.csv_analyse(
                    input=data["input"],
                    text_col=data.get("text_col", "Comment"),
                    id_col=data.get("id_col", "ID"),
                    prompt=data.get("prompt", "Summarise"),
                    save_csv=(data.get("save") or {}).get("csv"),
                    save_jsonl=(data.get("save") or {}).get("jsonl"),
                    connector=data.get("connector"),
                    rag_options=rag_options,
                )
            }
        if rtype == "text_files":
            return {
                "result": self.text_files(
                    prompt=data.get("prompt", "Summarise"),
                    connector=data.get("connector"),
                    select=data.get("select"),
                    save_jsonl=(data.get("save") or {}).get("jsonl"),
                    expects_json=bool(data.get("expects_json", True)),
                    rag_options=rag_options,
                )
            }
        if rtype == "images_analyse":
            return {
                "result": self.images_analyse(
                    prompt=data.get("prompt", "Describe"),
                    connector=data.get("connector"),
                    select=data.get("select"),
                    save_jsonl=(data.get("save") or {}).get("jsonl"),
                    expects_json=bool(data.get("expects_json", True)),
                    group_size=int(data.get("group_size", 0) or 0) or None,
                    rag_options=rag_options,
                )
            }
        raise ValueError(f"Unsupported or missing recipe type: {rtype!r}")

    # --- Helpers ---
    def _auto_connector_name(self) -> str:
        cfg = self._cfg
        if cfg is None:
            return "local_docs"
        connectors = getattr(cfg, "connectors", None) if not isinstance(cfg, dict) else cfg.get("connectors")
        if not connectors:
            return "local_docs"
        # Prefer first local connector, else first connector
        for c in connectors:
            t = getattr(c, "type", None) if not isinstance(c, dict) else c.get("type")
            if t == "local":
                return getattr(c, "name", None) if not isinstance(c, dict) else c.get("name")
        name = getattr(connectors[0], "name", None) if not isinstance(connectors[0], dict) else connectors[0].get("name")
        return name or "local_docs"


def _read_jsonl(path: str):
    import json

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)


# --- Additional SDK operations ---
def _build_text_chain(
    *,
    connector: str,
    select: List[str] | None,
    prompt: str,
    save_jsonl: str | None,
    expects_json: bool,
    rag_options: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    output_block: Any = "result"
    if expects_json:
        output_block = {"name": "result", "expects": "json", "parse_retries": 1}
    step = {
        "id": "s",
        "prompt": f"inline: {prompt}\n{{{{ text }}}}",
        "inputs": {"text": "${chunk.text}"},
        "output": output_block,
    }
    rag_cfg = _build_rag_block(rag_options, default_text_var="rag_context", default_image_var="rag_images")
    if rag_cfg:
        step["rag"] = rag_cfg
    return {
        "name": "text-files",
        "inputs": {"connector": connector, "select": select or ["**/*.{md,txt,html}"]},
        "steps": [step],
        "outputs": ([{"save": save_jsonl, "from": "result", "as": "jsonl"}] if save_jsonl else []),
    }


def _build_images_chain(
    *,
    connector: str,
    select: List[str] | None,
    prompt: str,
    save_jsonl: str | None,
    expects_json: bool,
    rag_options: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    output_block: Any = "analysis"
    if expects_json:
        output_block = {"name": "analysis", "expects": "json", "parse_retries": 1}
    step = {
        "id": "vision",
        "mode": "multimodal",
        "prompt": f"inline: {prompt}",
        "inputs": {},
        "output": output_block,
    }
    rag_cfg = _build_rag_block(rag_options, default_text_var="rag_context", default_image_var="rag_samples")
    if rag_cfg:
        step["rag"] = rag_cfg
    return {
        "name": "images-analyse",
        "inputs": {"connector": connector, "select": select or ["**/*.{png,jpg,jpeg}"]},
        "steps": [step],
        "outputs": ([{"save": save_jsonl, "from": "analysis", "as": "jsonl"}] if save_jsonl else []),
    }


def _build_images_group_chain(
    *,
    connector: str,
    select: List[str] | None,
    prompt: str,
    save_jsonl: str | None,
    expects_json: bool,
    group_size: int,
    rag_options: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    output_block: Any = "analysis"
    if expects_json:
        output_block = {"name": "analysis", "expects": "json", "parse_retries": 1}
    step = {
        "id": "vision",
        "mode": "multimodal",
        "prompt": f"inline: {prompt}",
        "inputs": {},
        "output": output_block,
    }
    rag_cfg = _build_rag_block(rag_options, default_text_var="rag_context", default_image_var="rag_samples")
    if rag_cfg:
        step["rag"] = rag_cfg
    return {
        "name": "images-analyse-group",
        "inputs": {"connector": connector, "select": select or ["**/*.{png,jpg,jpeg}"], "mode": "images_group", "images": {"group_size": group_size}},
        "steps": [step],
        "outputs": ([{"save": save_jsonl, "from": "analysis", "as": "jsonl"}] if save_jsonl else []),
    }


def _build_rag_block(
    rag_options: Dict[str, Any] | None,
    *,
    default_text_var: str | None = "rag_context",
    default_image_var: str | None = "rag_images",
) -> Dict[str, Any] | None:
    if not rag_options:
        return None
    pipeline = rag_options.get("pipeline")
    if not pipeline:
        return None

    cfg = dict(rag_options)
    cfg["pipeline"] = pipeline

    if "top_k_text" in cfg and cfg["top_k_text"] is not None:
        try:
            cfg["top_k_text"] = max(0, int(cfg["top_k_text"]))
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid top_k_text value: {cfg['top_k_text']!r}") from exc

    has_images = False
    if "top_k_images" in cfg and cfg["top_k_images"] is not None:
        try:
            cfg["top_k_images"] = max(0, int(cfg["top_k_images"]))
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid top_k_images value: {cfg['top_k_images']!r}") from exc
        has_images = cfg["top_k_images"] > 0
    else:
        cfg.pop("top_k_images", None)

    if "text_var" not in cfg and default_text_var:
        cfg["text_var"] = default_text_var

    if has_images:
        if "image_var" not in cfg and default_image_var:
            cfg["image_var"] = default_image_var
    else:
        cfg.pop("image_var", None)

    if "inject_prompt" not in cfg:
        cfg["inject_prompt"] = True

    return cfg
