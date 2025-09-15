from __future__ import annotations

import csv
import io
from typing import Any, Dict, Iterable, List, Optional

from .errors import ProcessingError


def _clean_headers(headers: List[Any]) -> List[str]:
    out: List[str] = []
    for h in headers:
        if h is None:
            out.append("")
        else:
            out.append(str(h).strip())
    # de-duplicate empty or repeated headers by numbering
    seen: Dict[str, int] = {}
    final: List[str] = []
    for h in out:
        base = h or "col"
        idx = seen.get(base, 0)
        if idx == 0:
            final.append(base)
        else:
            final.append(f"{base}_{idx}")
        seen[base] = idx + 1
    return final


def iter_table_rows(
    *,
    filename: str,
    data: bytes,
    text_column: str | List[str] | None = None,
    pass_through: Optional[List[str]] = None,
    header_row: int = 1,
) -> Iterable[Dict[str, Any]]:
    """Yield dict rows from a tabular file (CSV/XLSX/Parquet).

    - text_column: a column name or list of names whose values are concatenated into row["text"].
    - pass_through: Optional list of columns to include; when None, include all columns.
    - header_row: currently supports 1 (first row). Other values raise ProcessingError.
    """
    import os

    ext = os.path.splitext(filename)[1].lower()
    rows: List[Dict[str, Any]] = []

    if header_row not in (1,):
        raise ProcessingError("Only header_row=1 is supported currently")

    if ext == ".csv":
        f = io.StringIO(data.decode("utf-8", errors="replace"))
        reader = csv.reader(f)
        all_rows = [list(r) for r in reader]
        if not all_rows:
            return []
        headers = _clean_headers(all_rows[0])
        for r in all_rows[1:]:
            rec = {headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))}
            rows.append(rec)
    elif ext == ".xlsx":
        try:
            import openpyxl  # type: ignore
        except Exception as e:
            raise ProcessingError("XLSX support requires openpyxl (install extras: '.[excel]')") from e
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        it = ws.iter_rows(values_only=True)
        try:
            headers_raw = next(it)
        except StopIteration:
            headers_raw = []
        headers = _clean_headers(["" if v is None else v for v in headers_raw])
        for row in it:
            r = ["" if v is None else str(v) for v in row]
            rec = {headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))}
            rows.append(rec)
    elif ext == ".parquet":
        try:
            import pyarrow.parquet as pq  # type: ignore
        except Exception as e:
            raise ProcessingError("Parquet support requires pyarrow") from e
        table = pq.read_table(io.BytesIO(data))
        cols = list(table.schema.names)
        for i in range(table.num_rows):
            rec = {c: table.column(c)[i].as_py() for c in cols}
            rows.append(rec)
    else:
        raise ProcessingError(f"Unsupported table format: {ext}")

    # Apply pass_through filter if provided
    if pass_through is not None:
        filt = set(pass_through)
        rows = [{k: v for k, v in r.items() if k in filt} for r in rows]

    # Compute text field when requested
    if text_column:
        if isinstance(text_column, str):
            for r in rows:
                r["text"] = str(r.get(text_column, ""))
        else:
            cols = list(text_column)
            for r in rows:
                r["text"] = " ".join(str(r.get(c, "")) for c in cols if c in r)

    return rows


__all__ = ["iter_table_rows"]

