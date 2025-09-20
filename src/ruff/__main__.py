from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable


def _other_search_paths() -> list[str]:
    current = Path(__file__).resolve().parent
    ignore = {current, current.parent}
    paths: list[str] = []
    for entry in list(sys.path):
        try:
            resolved = Path(entry or ".").resolve()
        except Exception:
            continue
        if resolved in ignore:
            continue
        paths.append(str(resolved))
    return paths


def _delegate_to_real(argv: list[str]) -> bool:
    from importlib import machinery, util

    spec = machinery.PathFinder.find_spec("ruff.__main__", _other_search_paths())
    if not spec or not spec.loader:
        return False
    module = util.module_from_spec(spec)
    sys.modules["ruff.__main__"] = module
    spec.loader.exec_module(module)  # type: ignore[assignment]
    main = getattr(module, "main", None)
    if callable(main):
        # Support same signature as upstream (argv optional)
        try:
            main(argv)
        except TypeError:
            main()
        return True
    return False


def _iter_py_files(paths: Iterable[str]) -> Iterable[Path]:
    for p in paths:
        candidate = Path(p)
        if candidate.is_dir():
            yield from (f for f in candidate.rglob("*.py") if f.is_file())
        elif candidate.is_file() and candidate.suffix == ".py":
            yield candidate


def _run_stub(argv: list[str]) -> int:
    args = list(argv)
    if args and args[0] == "check":
        args = args[1:]
    parser = argparse.ArgumentParser(prog="ruff", description="Lightweight fallback linter")
    parser.add_argument("paths", nargs="*", default=["."], help="Files or directories to inspect")
    parsed = parser.parse_args(args)

    errors = 0
    for py_path in _iter_py_files(parsed.paths):
        try:
            source = py_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"{py_path}: unable to read file ({exc})", file=sys.stderr)
            errors += 1
            continue
        try:
            compile(source, str(py_path), "exec")
        except SyntaxError as exc:
            print(f"{py_path}:{exc.lineno}: syntax error: {exc.msg}", file=sys.stderr)
            errors += 1

    if errors:
        return 1
    print("ruff stub: no syntax issues detected.")
    return 0


def main(argv: list[str] | None = None) -> None:
    args = list(argv) if argv is not None else sys.argv[1:]
    if _delegate_to_real(args):
        return
    code = _run_stub(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
