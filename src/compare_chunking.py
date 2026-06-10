from __future__ import annotations

from dataclasses import dataclass

from src.rag_pipeline import Chunk, bm25_scores, build_chunks, load_documents


@dataclass(frozen=True)
class StrategyResult:
    strategy: str
    query: str
    top_chunk: str
    top_source: str


QUERIES = [
    "What should I watch for cyberpunk and landmark animation?",
    "What is a good gateway anime movie for someone new to anime?",
    "Which anime is emotionally devastating and not a comfort watch?",
]


def fixed_character_chunks(width: int = 450, overlap: int = 50) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in load_documents():
        start = 0
        index = 1
        while start < len(doc.text):
            text = doc.text[start : start + width].strip()
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.path.stem}::fixed-{index}",
                    text=text,
                    metadata={
                        "source_file": doc.path.name,
                        "title": doc.title,
                        "category": doc.category,
                    },
                )
            )
            start += width - overlap
            index += 1
    return chunks


def top_bm25(query: str, chunks: list[Chunk], strategy: str) -> StrategyResult:
    scores = bm25_scores(query, chunks)
    best = max(chunks, key=lambda chunk: scores[chunk.chunk_id])
    return StrategyResult(strategy, query, best.text[:180].replace("\n", " "), str(best.metadata["source_file"]))


def main() -> None:
    paragraph_chunks = build_chunks(load_documents())
    fixed_chunks = fixed_character_chunks()
    print(f"Paragraph-aware chunks: {len(paragraph_chunks)}")
    print(f"Fixed-character chunks: {len(fixed_chunks)}")
    for query in QUERIES:
        print(f"\nQuery: {query}")
        for result in [
            top_bm25(query, paragraph_chunks, "paragraph-aware 1000/160"),
            top_bm25(query, fixed_chunks, "fixed 450/50"),
        ]:
            print(f"- {result.strategy}: {result.top_source} -> {result.top_chunk}...")


if __name__ == "__main__":
    main()
