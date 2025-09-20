"""Show deterministic document and chunk identifiers derived from content hashes."""

from __future__ import annotations

from fmf.processing.loaders import load_document_from_bytes
from fmf.processing.chunking import chunk_text


def main() -> None:
    payload = b"Paragraph one. Paragraph two."
    doc1 = load_document_from_bytes(
        source_uri="file:///demo.txt",
        filename="demo.txt",
        data=payload,
        processing_cfg={"text": {"chunking": {"splitter": "by_sentence", "max_tokens": 20}}},
    )
    doc2 = load_document_from_bytes(
        source_uri="file:///demo.txt",
        filename="demo.txt",
        data=payload,
        processing_cfg={},
    )
    print("document IDs equal:", doc1.id == doc2.id)
    print("provenance:", doc1.provenance)

    chunks = chunk_text(doc_id=doc1.id, text=doc1.text or "", splitter="by_sentence")
    for chunk in chunks:
        print(f"chunk {chunk.provenance['index']}: id={chunk.id} length={chunk.provenance['length_chars']}")


if __name__ == "__main__":
    main()
