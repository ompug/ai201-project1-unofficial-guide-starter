from __future__ import annotations

import argparse
import html
import math
import os
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

try:
    from groq import Groq
except Exception:  # pragma: no cover - optional runtime dependency
    Groq = None


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = ROOT / "documents" / "raw"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION_NAME = "must_watch_anime_guide"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 160
TOP_K = 5
HYBRID_SEMANTIC_WEIGHT = 0.65
HYBRID_BM25_WEIGHT = 0.35


@dataclass(frozen=True)
class SourceDocument:
    path: Path
    title: str
    source: str
    date: str
    category: str
    rating: int
    text: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    metadata: dict[str, str | int]


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    text: str
    metadata: dict[str, str | int]
    score: float
    semantic_score: float
    bm25_score: float = 0.0


def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\b(cookie banner|share this|read more|advertisement)\b", " ", text, flags=re.I)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_documents(documents_dir: Path = DOCUMENTS_DIR) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    for path in sorted(documents_dir.glob("*.txt")):
        raw = path.read_text(encoding="utf-8")
        header_text, _, body = raw.partition("\n\n")
        headers: dict[str, str] = {}
        for line in header_text.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        title = headers.get("title", path.stem)
        docs.append(
            SourceDocument(
                path=path,
                title=title,
                source=headers.get("source", f"Local file: {path.name}"),
                date=headers.get("date", "unknown"),
                category=headers.get("category", "uncategorized"),
                rating=int(headers.get("rating", "0") or 0),
                text=clean_text(body),
            )
        )
    return docs


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
            continue
        if current:
            pieces.append(current)
        current = sentence
    if current:
        pieces.append(current)
    return pieces


def _clean_overlap_tail(text: str, overlap: int) -> str:
    tail = text[-overlap:].strip()
    sentence_boundary = re.search(r"[.!?]\s+", tail)
    if sentence_boundary and len(tail[sentence_boundary.end() :].strip()) >= 60:
        tail = tail[sentence_boundary.end() :].strip()
    elif tail and not re.match(r"^[A-Z0-9\"']", tail):
        first_space = tail.find(" ")
        if first_space != -1:
            tail = tail[first_space + 1 :].strip()
    return tail


def chunk_text(text: str, max_chars: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    paragraphs: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_chars:
            paragraphs.append(para)
        else:
            paragraphs.extend(_split_long_paragraph(para, max_chars))

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
            tail = _clean_overlap_tail(current, overlap)
            current = f"{tail}\n\n{para}".strip() if tail else para
        else:
            chunks.append(para)
            current = ""
    if current:
        chunks.append(current)
    return chunks


def build_chunks(documents: Iterable[SourceDocument]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in documents:
        for index, text in enumerate(chunk_text(doc.text), start=1):
            chunk_id = f"{doc.path.stem}::chunk-{index}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=text,
                    metadata={
                        "source_file": doc.path.name,
                        "title": doc.title,
                        "source": doc.source,
                        "date": doc.date,
                        "category": doc.category,
                        "rating": doc.rating,
                        "chunk_index": index,
                    },
                )
            )
    return chunks


def get_collection(reset: bool = False):
    if reset and CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )


def index_documents(reset: bool = True) -> list[Chunk]:
    chunks = build_chunks(load_documents())
    collection = get_collection(reset=reset)
    if chunks:
        collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
        )
    return chunks


def ensure_index() -> None:
    if not CHROMA_DIR.exists():
        index_documents(reset=True)
        return
    collection = get_collection(reset=False)
    if collection.count() == 0:
        index_documents(reset=True)


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9.\-]*", text.lower())


def bm25_scores(query: str, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> dict[str, float]:
    query_terms = tokenize(query)
    if not query_terms or not chunks:
        return {chunk.chunk_id: 0.0 for chunk in chunks}

    tokenized = [tokenize(chunk.text) for chunk in chunks]
    avgdl = sum(len(tokens) for tokens in tokenized) / max(len(tokenized), 1)
    doc_freq: Counter[str] = Counter()
    for tokens in tokenized:
        doc_freq.update(set(tokens))

    scores: dict[str, float] = {}
    for chunk, tokens in zip(chunks, tokenized):
        tf = Counter(tokens)
        score = 0.0
        for term in query_terms:
            if term not in tf:
                continue
            idf = math.log(1 + (len(chunks) - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            numerator = tf[term] * (k1 + 1)
            denominator = tf[term] + k1 * (1 - b + b * len(tokens) / max(avgdl, 1))
            score += idf * numerator / denominator
        scores[chunk.chunk_id] = score
    return scores


def _normalize(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    high = max(values.values())
    low = min(values.values())
    if math.isclose(high, low):
        return {key: 1.0 if high > 0 else 0.0 for key in values}
    return {key: (value - low) / (high - low) for key, value in values.items()}


def semantic_search(query: str, top_k: int = TOP_K, category: str | None = None) -> list[SearchResult]:
    ensure_index()
    collection = get_collection(reset=False)
    where = {"category": category} if category else None
    output = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    results: list[SearchResult] = []
    for chunk_id, text, metadata, distance in zip(
        output["ids"][0],
        output["documents"][0],
        output["metadatas"][0],
        output["distances"][0],
    ):
        semantic_score = 1 / (1 + float(distance))
        results.append(
            SearchResult(
                chunk_id=chunk_id,
                text=text,
                metadata=metadata,
                score=semantic_score,
                semantic_score=semantic_score,
            )
        )
    return results


def hybrid_search(query: str, top_k: int = TOP_K, category: str | None = None) -> list[SearchResult]:
    ensure_index()
    all_chunks = build_chunks(load_documents())
    if category:
        all_chunks = [chunk for chunk in all_chunks if chunk.metadata["category"] == category]

    collection = get_collection(reset=False)
    semantic_n = max(len(all_chunks), top_k)
    where = {"category": category} if category else None
    output = collection.query(
        query_texts=[query],
        n_results=semantic_n,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    semantic_raw = {
        chunk_id: 1 / (1 + float(distance))
        for chunk_id, distance in zip(output["ids"][0], output["distances"][0])
    }
    bm25_raw = bm25_scores(query, all_chunks)
    semantic_norm = _normalize(semantic_raw)
    bm25_norm = _normalize(bm25_raw)

    chunk_by_id = {chunk.chunk_id: chunk for chunk in all_chunks}
    results: list[SearchResult] = []
    for chunk_id, chunk in chunk_by_id.items():
        semantic_score = semantic_norm.get(chunk_id, 0.0)
        bm25_score = bm25_norm.get(chunk_id, 0.0)
        score = HYBRID_SEMANTIC_WEIGHT * semantic_score + HYBRID_BM25_WEIGHT * bm25_score
        results.append(
            SearchResult(
                chunk_id=chunk_id,
                text=chunk.text,
                metadata=chunk.metadata,
                score=score,
                semantic_score=semantic_raw.get(chunk_id, 0.0),
                bm25_score=bm25_raw.get(chunk_id, 0.0),
            )
        )
    return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]


def retrieve(query: str, mode: str = "hybrid", top_k: int = TOP_K, category: str | None = None) -> list[SearchResult]:
    if mode == "semantic":
        return semantic_search(query, top_k=top_k, category=category)
    if mode == "hybrid":
        return hybrid_search(query, top_k=top_k, category=category)
    raise ValueError(f"Unknown retrieval mode: {mode}")


def _source_label(result: SearchResult) -> str:
    return str(result.metadata.get("source_file", result.chunk_id))


def _answer_with_groq(query: str, results: list[SearchResult]) -> str | None:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_key_here" or Groq is None:
        return None

    context = "\n\n".join(
        f"[{_source_label(result)}]\n{result.text}" for result in results
    )
    system_prompt = (
        "You answer only from the retrieved context. If the answer is not supported, "
        "refuse and say the corpus does not contain enough information. Cite source "
        "file names in brackets after every factual claim."
    )
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()


def grounded_answer(query: str, results: list[SearchResult]) -> str:
    lowered_query = query.lower()
    if any(term in lowered_query for term in ["where can i stream", "streaming in", "netflix in", "crunchyroll price", "release date for season 2"]):
        return "I do not have enough information in the must-watch anime guide corpus to answer that. The guide covers recommendation fit and acclaim, not current streaming availability, prices, or future release schedules."

    if not results or results[0].score < 0.12:
        return "I do not have enough information in the must-watch anime guide corpus to answer that. Please ask about the anime titles, moods, genres, recommendation fit, or source-backed acclaim covered by the guide."

    groq_answer = _answer_with_groq(query, results)
    if groq_answer:
        return groq_answer

    query_terms = set(tokenize(query))
    selected: list[str] = []
    used_sources: list[str] = []
    usable_results = [result for result in results[:3] if result.score >= 0.45 or result == results[0]]
    for result_index, result in enumerate(usable_results):
        sentences = re.split(r"(?<=[.!?])\s+", result.text)
        label = _source_label(result)
        if result_index == 0:
            for sentence in [sentence.strip() for sentence in sentences[:2] if sentence.strip()]:
                cited = f"{sentence} [{label}]"
                if cited not in selected:
                    selected.append(cited)
                    used_sources.append(label)

        ranked = sorted(
            ((sentence.strip(), len(query_terms.intersection(tokenize(sentence)))) for sentence in sentences),
            key=lambda item: item[1],
            reverse=True,
        )
        added_for_source = 0
        for sentence, overlap_count in ranked:
            if not sentence or (overlap_count == 0 and added_for_source > 0):
                continue
            cited = f"{sentence} [{label}]"
            if cited not in selected:
                selected.append(cited)
                used_sources.append(label)
                added_for_source += 1
            if added_for_source >= 1:
                break

    if not selected:
        return "I do not have enough information in the retrieved documents to answer that."
    unique_sources = ", ".join(dict.fromkeys(used_sources))
    return " ".join(selected) + f"\n\nSources: {unique_sources}"


def format_results(results: list[SearchResult]) -> str:
    lines: list[str] = []
    for index, result in enumerate(results, start=1):
        title = result.metadata.get("title", result.chunk_id)
        source_file = result.metadata.get("source_file", result.chunk_id)
        snippet = result.text.replace("\n", " ")
        if len(snippet) > 260:
            snippet = snippet[:257].rstrip() + "..."
        lines.append(
            f"{index}. {source_file} | {title} | score={result.score:.3f} "
            f"(semantic={result.semantic_score:.3f}, bm25={result.bm25_score:.3f})\n"
            f"   {snippet}"
        )
    return "\n".join(lines)


def inspect_chunks(limit: int = 5) -> str:
    chunks = build_chunks(load_documents())
    lines = [f"Total chunks: {len(chunks)}"]
    for chunk in chunks[:limit]:
        lines.append(f"\n[{chunk.metadata['source_file']} / {chunk.chunk_id}]\n{chunk.text}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and inspect the must-watch anime RAG pipeline.")
    parser.add_argument("--reindex", action="store_true", help="Rebuild the ChromaDB index.")
    parser.add_argument("--inspect-chunks", action="store_true", help="Print representative chunks.")
    args = parser.parse_args()

    if args.reindex:
        chunks = index_documents(reset=True)
        print(f"Indexed {len(chunks)} chunks into {CHROMA_DIR}.")
    if args.inspect_chunks:
        print(inspect_chunks())


if __name__ == "__main__":
    main()
