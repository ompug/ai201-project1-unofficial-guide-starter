from __future__ import annotations

import argparse

from src.rag_pipeline import TOP_K, format_results, grounded_answer, retrieve


def run_query(
    question: str,
    mode: str = "hybrid",
    top_k: int = TOP_K,
    category: str | None = None,
    show_chunks: bool = False,
) -> str:
    results = retrieve(question, mode=mode, top_k=top_k, category=category)
    answer = grounded_answer(question, results)
    output = [f"Question: {question}", f"Mode: {mode}", f"Answer:\n{answer}"]
    if show_chunks:
        output.append("Retrieved chunks:\n" + format_results(results))
    return "\n\n".join(output)


def interactive(mode: str, top_k: int, category: str | None, show_chunks: bool) -> None:
    print("AI201 Unofficial Guide. Type 'exit' to quit.")
    previous_question: str | None = None
    while True:
        question = input("\nQuestion: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        expanded = question
        if previous_question:
            expanded = f"Previous question: {previous_question}\nFollow-up question: {question}"
        print(run_query(expanded, mode=mode, top_k=top_k, category=category, show_chunks=show_chunks))
        previous_question = question


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the AI201 Project 1 unofficial guide.")
    parser.add_argument("question", nargs="?", help="Question to ask the RAG system.")
    parser.add_argument("--mode", choices=["semantic", "hybrid"], default="hybrid")
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--category", help="Optional metadata category filter, such as retrieval or evaluation.")
    parser.add_argument("--show-chunks", action="store_true", help="Show retrieved chunks after the answer.")
    parser.add_argument("--interactive", action="store_true", help="Start a multi-turn CLI session.")
    args = parser.parse_args()

    if args.interactive:
        interactive(args.mode, args.top_k, args.category, args.show_chunks)
        return
    if not args.question:
        parser.error("provide a question or use --interactive")
    print(run_query(args.question, mode=args.mode, top_k=args.top_k, category=args.category, show_chunks=args.show_chunks))


if __name__ == "__main__":
    main()
