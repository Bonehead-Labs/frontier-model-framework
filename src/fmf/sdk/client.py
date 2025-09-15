from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ..chain.runner import run_chain_config
from ..config.loader import load_config


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

