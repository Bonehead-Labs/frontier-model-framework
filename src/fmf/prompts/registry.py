from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class PromptVersion:
    id: str
    version: str
    template: str
    content_hash: str
    path: str


class PromptRegistryError(Exception):
    pass


class LocalYamlRegistry:
    def __init__(self, *, root: str, index_file: str) -> None:
        self.root = os.path.abspath(root)
        self.index_file = index_file if os.path.isabs(index_file) else os.path.join(self.root, index_file)
        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)

    def _load_index(self) -> Dict[str, Any]:
        if not os.path.exists(self.index_file):
            return {"prompts": []}
        with open(self.index_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"prompts": []}

    def _save_index(self, data: Dict[str, Any]) -> None:
        with open(self.index_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False)

    def register(self, ref: str) -> PromptVersion:
        """Register a prompt from a YAML file ref like path#version.

        Validates required fields, computes content hash, updates index.
        """
        path = ref
        version = None
        if "#" in ref:
            path, version = ref.split("#", 1)
        if not os.path.isabs(path):
            path = os.path.join(self.root, path)
        if not os.path.exists(path):
            raise PromptRegistryError(f"Prompt file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        pid = data.get("id") or os.path.splitext(os.path.basename(path))[0]
        versions = data.get("versions")
        if not versions:
            # allow single template at top-level
            templ = data.get("template")
            if not templ:
                raise PromptRegistryError("Prompt YAML must contain 'template' or 'versions'")
            use_ver = data.get("version", "v0") if version is None else version
            pv = PromptVersion(id=pid, version=use_ver, template=templ, content_hash=_compute_hash(templ), path=path)
        else:
            if version is None:
                raise PromptRegistryError("Version must be provided for multi-version prompt (use file#version)")
            match = None
            for ver in versions:
                if ver.get("version") == version:
                    match = ver
                    break
            if not match:
                raise PromptRegistryError(f"Version {version!r} not found in {path}")
            templ = match.get("template")
            if not templ:
                raise PromptRegistryError(f"Version {version!r} missing template in {path}")
            pv = PromptVersion(id=pid, version=version, template=templ, content_hash=_compute_hash(templ), path=path)

        # Optional validation tests from YAML
        for ver in (data.get("versions") or []):
            if ver.get("version") == pv.version and ver.get("tests"):
                for t in ver["tests"]:
                    inputs = t.get("inputs", {})
                    rendered = _render_simple(pv.template, inputs)
                    contains = t.get("assertions", {}).get("contains", [])
                    for needle in contains:
                        if needle not in rendered:
                            raise PromptRegistryError(f"Prompt test failed: '{needle}' not in rendered output")

        # Update index
        index = self._load_index()
        found = None
        for p in index.get("prompts", []):
            if p.get("id") == pv.id:
                found = p
                break
        if not found:
            found = {"id": pv.id, "path": os.path.relpath(pv.path, self.root), "versions": []}
            index.setdefault("prompts", []).append(found)
        # upsert version
        vlist = found.setdefault("versions", [])
        for v in vlist:
            if v.get("version") == pv.version:
                v["content_hash"] = pv.content_hash
                break
        else:
            vlist.append({"version": pv.version, "content_hash": pv.content_hash})
        self._save_index(index)
        return pv

    def get(self, id_version: str) -> PromptVersion:
        pid, ver = id_version.split("#", 1)
        index = self._load_index()
        for p in index.get("prompts", []):
            if p.get("id") == pid:
                path = p.get("path")
                if not os.path.isabs(path):
                    path = os.path.join(self.root, path)
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                for vv in (data.get("versions") or []):
                    if vv.get("version") == ver:
                        templ = vv.get("template")
                        if not templ:
                            raise PromptRegistryError("Template missing for version")
                        return PromptVersion(id=pid, version=ver, template=templ, content_hash=_compute_hash(templ), path=path)
                # try top-level template
                if data.get("version") == ver and data.get("template"):
                    templ = data["template"]
                    return PromptVersion(id=pid, version=ver, template=templ, content_hash=_compute_hash(templ), path=path)
        raise PromptRegistryError(f"Prompt {id_version!r} not found")


def _render_simple(template: str, inputs: Dict[str, Any]) -> str:
    out = template
    for k, v in inputs.items():
        out = out.replace("{{ " + k + " }}", str(v))
    return out


def build_prompt_registry(cfg: Any | None):
    # Supports only local_yaml/git_yaml paths for now (both on disk)
    backend = None
    root = os.getcwd()
    index_file = "prompts/index.yaml"
    if cfg is not None:
        backend = getattr(cfg, "backend", None) if not isinstance(cfg, dict) else cfg.get("backend")
        root = getattr(cfg, "path", root) if not isinstance(cfg, dict) else cfg.get("path", root)
        index_file = getattr(cfg, "index_file", index_file) if not isinstance(cfg, dict) else cfg.get("index_file", index_file)
    return LocalYamlRegistry(root=root, index_file=index_file)


__all__ = [
    "PromptVersion",
    "PromptRegistryError",
    "LocalYamlRegistry",
    "build_prompt_registry",
]

