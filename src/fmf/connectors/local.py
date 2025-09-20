from __future__ import annotations

import fnmatch
import os
import pathlib
import datetime as dt
from typing import IO, Iterable, List, Optional

from ..core.interfaces import ConnectorSpec, ConnectorSelectors, RunContext
from ..core.interfaces.connectors_base import BaseConnector
from .base import ResourceRef, ResourceInfo, ConnectorError


class LocalConnector(BaseConnector):
    def __init__(
        self,
        *,
        spec: ConnectorSpec | None = None,
        name: str | None = None,
        root: str | None = None,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
    ) -> None:
        if spec is None:
            if name is None or root is None:
                raise ValueError("LocalConnector requires either a spec or name/root parameters")
            selectors = ConnectorSelectors(
                include=list(include or ["**/*"]),
                exclude=list(exclude or []),
            )
            spec = ConnectorSpec(name=name, type="local", selectors=selectors, options={"root": root})
        super().__init__(spec)
        self.root = os.path.abspath(spec.options.get("root", root or "."))
        self._include = list(spec.selectors.include or ["**/*"])
        self._exclude = list(spec.selectors.exclude or [])

    def _iter_paths(self, selector: List[str] | None) -> Iterable[pathlib.Path]:
        patterns = selector or self._include
        seen: set[str] = set()
        # Precompute recursive list once to avoid repeated walks for multiple patterns
        all_rel_files: Optional[list[str]] = None
        for pat in patterns:
            abs_pattern = os.path.join(self.root, pat)
            if "**" in pat:
                if all_rel_files is None:
                    all_rel_files = list(_rglob_files(self.root))
                # Match explicitly against pattern; include top-level fallback when pattern starts with '**/'
                candidates = []
                for rel in all_rel_files:
                    if fnmatch.fnmatchcase(rel, pat) or (pat.startswith("**/") and fnmatch.fnmatchcase(rel, pat[3:])):
                        candidates.append(os.path.join(self.root, rel))
                iterator = candidates
            else:
                iterator = _glob_files(abs_pattern)

            for path_str in iterator:
                p = pathlib.Path(path_str)
                if not p.is_file():
                    continue
                rel = p.relative_to(self.root).as_posix()
                if any(fnmatch.fnmatchcase(rel, ex) for ex in self._exclude):
                    continue
                if rel in seen:
                    continue
                seen.add(rel)
                yield p

    def list(
        self,
        *,
        selector: list[str] | None = None,
        context: RunContext | None = None,
    ) -> Iterable[ResourceRef]:
        for p in self._iter_paths(selector):
            rel = p.relative_to(self.root).as_posix()
            yield ResourceRef(id=rel, uri=p.resolve().as_uri(), name=p.name)

    def open(
        self,
        ref: ResourceRef,
        *,
        mode: str = "rb",
        context: RunContext | None = None,
    ) -> IO[bytes]:
        path = pathlib.Path(self.root, ref.id)
        if not path.is_file():
            raise ConnectorError(f"Resource not found: {ref.id}")
        # Ensure binary mode by default for bytes interface
        if "b" not in mode:
            mode = mode + "b"
        return open(path, mode)

    def info(self, ref: ResourceRef, *, context: RunContext | None = None) -> ResourceInfo:
        path = pathlib.Path(self.root, ref.id)
        if not path.exists():
            raise ConnectorError(f"Resource not found: {ref.id}")
        st = path.stat()
        mtime = dt.datetime.fromtimestamp(st.st_mtime, tz=dt.timezone.utc)
        return ResourceInfo(
            source_uri=path.resolve().as_uri(),
            modified_at=mtime,
            etag=None,
            size=st.st_size,
            extra={"path": str(path)},
        )


def _glob_files(abs_pattern: str) -> Iterable[str]:
    # Simple non-recursive glob expansion
    root = os.path.dirname(abs_pattern)
    pattern = os.path.basename(abs_pattern)
    try:
        for name in os.listdir(root):
            if fnmatch.fnmatchcase(name, pattern):
                yield os.path.join(root, name)
    except FileNotFoundError:
        return


def _rglob_files(root: str) -> Iterable[str]:
    # Generate relative POSIX paths for all files under root recursively
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            abs_path = os.path.join(dirpath, fn)
            rel = os.path.relpath(abs_path, root).replace(os.sep, "/")
            yield rel


__all__ = ["LocalConnector"]
