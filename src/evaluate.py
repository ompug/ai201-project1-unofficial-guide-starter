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
        "What is a good gateway anime movie for someone new to anime?",
        "Spirited Away is a strong gateway film; Your Name is also a modern accessible option.",
    ),
    EvalCase(
        "Which anime should I watch for cyberpunk and landmark animation?",
        "Akira.",
    ),
    EvalCase(
        "What should I watch if I want a complete adventure series with a strong ending?",
        "Fullmetal Alchemist: Brotherhood.",
    ),
    EvalCase(
        "Which recommendation fits a recent thoughtful fantasy about memory and grief?",
        "Frieren: Beyond Journey's End.",
    ),
    EvalCase(
        "What anime should I avoid recommending as a casual comfort watch because it is emotionally devastating?",
        "Grave of the Fireflies.",
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
