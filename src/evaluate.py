from __future__ import annotations

from dataclasses import dataclass

from src.query import run_query
from src.rag_pipeline import format_results, retrieve


@dataclass(frozen=True)
class EvalCase:
    question: str
    expected: str


EVAL_CASES = [
    EvalCase(
        "How many source documents does the project need, and how should they be identified?",
        "At least 10 documents, identified with specific URLs, subreddit names, file paths, or file descriptions.",
    ),
    EvalCase(
        "What chunk size and overlap does this project use, and why?",
        "900 characters with 180 characters of overlap, to preserve short advice thoughts while protecting transitions.",
    ),
    EvalCase(
        "Which embedding model is used, and what top-k value does retrieval use?",
        "sentence-transformers/all-MiniLM-L6-v2 with top-k 5.",
    ),
    EvalCase(
        "What must the system do when a query is not supported by the retrieved documents?",
        "Refuse to answer and say the corpus does not contain enough information instead of guessing.",
    ),
    EvalCase(
        "What does the README evaluation report need to include for each of the five test questions?",
        "The question, expected answer, actual system response, retrieved chunks, and an accuracy judgment.",
    ),
]


def main() -> None:
    for index, case in enumerate(EVAL_CASES, start=1):
        print(f"\n=== Evaluation {index} ===")
        print(f"Question: {case.question}")
        print(f"Expected: {case.expected}")
        print(run_query(case.question, mode="hybrid", show_chunks=False))
        print("Retrieved chunks:")
        print(format_results(retrieve(case.question, mode="hybrid", top_k=3)))


if __name__ == "__main__":
    main()
