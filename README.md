# The Unofficial Guide - CodePath AI201 Project 1

This project is a local RAG system for an unofficial student survival guide to CodePath AI201 Project 1. The domain is valuable because the assignment and rubric contain many small requirements that are easy to miss, such as labeled sample chunks, out-of-scope refusal, retrieval explanations, and AI usage transparency. The system makes those scattered requirements searchable with grounded, cited answers.

## Run It

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.rag_pipeline --reindex --inspect-chunks
python -m src.query "What chunk size and overlap does this project use?" --mode hybrid --show-chunks
python -m src.evaluate
```

If `GROQ_API_KEY` is set in `.env`, the generator can call Groq. Without a key, the project uses a deterministic grounded extractive fallback so the demo still works.

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Student Notes - Choosing the Project 1 Domain | Local peer note | `documents/raw/01_domain_and_scope.txt` |
| 2 | Student Notes - Document Collection Checklist | Local peer checklist | `documents/raw/02_document_collection.txt` |
| 3 | Student Notes - planning.md Must Be Written First | Local planning note | `documents/raw/03_planning_md_requirements.txt` |
| 4 | Student Notes - Chunking Strategy for Short Advice Documents | Local implementation note | `documents/raw/04_chunking_strategy.txt` |
| 5 | Student Notes - Ingestion and Cleaning | Local ingestion note | `documents/raw/05_ingestion_cleaning.txt` |
| 6 | Student Notes - Retrieval, Embeddings, and Hybrid Search | Local retrieval note | `documents/raw/06_retrieval_semantic_hybrid.txt` |
| 7 | Student Notes - Grounded Generation and Source Attribution | Local generation note | `documents/raw/07_grounded_generation.txt` |
| 8 | Student Notes - Query Interface Expectations | Local interface note | `documents/raw/08_query_interface.txt` |
| 9 | Student Notes - Evaluation Report and Failure Case | Local evaluation note | `documents/raw/09_evaluation_report.txt` |
| 10 | Student Notes - Stretch Feature Strategy | Local stretch-feature note | `documents/raw/10_stretch_features.txt` |
| 11 | Student Notes - AI Usage Transparency | Local reflection note | `documents/raw/11_ai_usage_transparency.txt` |
| 12 | Student Notes - Common Rubric Point Traps | Local rubric checklist | `documents/raw/12_rubric_point_traps.txt` |

## Document Pipeline

Ingestion loads every `.txt` file in `documents/raw/`, parses metadata fields (`Title`, `Source`, `Date`, `Category`, `Rating`), cleans HTML/noisy whitespace, and preserves metadata on every chunk. The final index contains 12 documents and 18 chunks.

**Chunk size:** 900 characters.  
**Overlap:** 180 characters.  
**Reasoning:** These are short advice documents, so 900 characters usually captures one complete recommendation plus context. The 180-character overlap protects transitions where a requirement and its explanation sit across adjacent paragraphs. The chunker prefers paragraph boundaries, then trims overlap at a clean word or sentence boundary.

### Sample Chunks

1. `01_domain_and_scope.txt`: "For this project, the domain is an unofficial student survival guide for CodePath AI201 Project 1... students can miss small scoring details such as sample chunks, out-of-scope refusal, and production embedding tradeoffs."
2. `02_document_collection.txt`: "The project needs at least ten specific documents, pages, threads, or files. The README should name the domain and identify the sources clearly enough that another person could locate them."
3. `03_planning_md_requirements.txt`: "`planning.md` should be completed before pipeline code. It needs substantive sections for Domain, Documents, Chunking Strategy, Retrieval Approach, Evaluation Plan, Anticipated Challenges, Architecture, and AI Tool Plan."
4. `04_chunking_strategy.txt`: "A target of about 900 characters works well for these documents because most important points fit in one to three paragraphs."
5. `07_grounded_generation.txt`: "The system prompt should explicitly say that if the answer is not supported by the retrieved context, the assistant must refuse and say the corpus does not contain enough information."

## Retrieval

**Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` through ChromaDB.  
**Vector store:** ChromaDB persisted in `chroma_db/`.  
**Top-k:** 5.  
**Hybrid search:** semantic score is combined with BM25 as `0.65 * semantic + 0.35 * BM25`.

Production model tradeoff: I chose `all-MiniLM-L6-v2` because it is free, local, private, and fast for a small English corpus. For production, I would weigh retrieval accuracy, context length, multilingual support, domain-specific language, latency, privacy, API reliability, and cost. A hosted larger embedding model might improve ambiguous queries but would add cost and external-service dependency.

### Retrieval Tests

| Query | Top returned chunks | Why relevant |
|---|---|---|
| "How many retrieval examples and sample chunks does the README need?" | `03_planning_md_requirements.txt`, `09_evaluation_report.txt`, `12_rubric_point_traps.txt` | Relevant because the first two identify retrieval-test requirements, and `12_rubric_point_traps.txt` names the five sample chunks and three retrieval examples. |
| "What does the interface need to show?" | `08_query_interface.txt`, `01_domain_and_scope.txt`, `11_ai_usage_transparency.txt` | Relevant because `08_query_interface.txt` directly describes CLI inputs/outputs and sample transcripts. The other chunks are less central but still related to demo artifacts. |
| "What AI usage transparency is required?" | `11_ai_usage_transparency.txt`, `02_document_collection.txt`, `03_planning_md_requirements.txt` | Relevant because the top chunk states the two required AI usage instances and what must be reviewed/revised. |

## Grounded Generation

Grounding is enforced in two ways. First, the prompt says: "You answer only from the retrieved context. If the answer is not supported, refuse and say the corpus does not contain enough information. Cite source file names in brackets after every factual claim." Second, the fallback generator only extracts sentences from retrieved chunks and prints source filenames after claims. The pipeline also refuses obvious out-of-scope queries.

Example response 1:

> The project needs at least ten specific documents, pages, threads, or files. [02_document_collection.txt] The README should name the domain and identify the sources clearly enough that another person could locate them. [02_document_collection.txt]

Example response 2:

> The AI Usage section should describe at least two specific instances of AI tool use. [11_ai_usage_transparency.txt] Each instance should say what the student directed the tool to do, what input was provided, what output was produced, and what the student reviewed, revised, or overrode. [11_ai_usage_transparency.txt]

Out-of-scope refusal:

> Query: What is the housing deposit deadline for UCLA?  
> Response: I do not have enough information in the AI201 Project 1 guide corpus to answer that. The retrieved guide only covers AI201 Project 1 requirements, so answering a campus housing deadline would require unsupported outside knowledge.

## Query Interface

The interface is a CLI in `src/query.py`.

Inputs: required question text; optional `--mode semantic|hybrid`; optional `--top-k`; optional `--category`; optional `--show-chunks`; optional `--interactive`.

Outputs: the question, retrieval mode, grounded answer with source citations, and retrieved chunk list when `--show-chunks` is enabled.

Sample transcript:

```text
$ python -m src.query "What does the interface need to show?" --mode hybrid --category interface --show-chunks
Question: What does the interface need to show?
Mode: hybrid
Answer:
The interface can be simple as long as it is usable in a demo. [08_query_interface.txt] A command-line interface is acceptable if it clearly accepts a question, optional search mode, optional metadata filters, and prints an answer with citations. [08_query_interface.txt]
Retrieved chunks:
1. 08_query_interface.txt | Student Notes - Query Interface Expectations | score=1.000 ...
```

## Evaluation Report

| # | Question | Expected answer | System response summary | Retrieved chunks | Accuracy |
|---|----------|-----------------|-------------------------|------------------|----------|
| 1 | How many source documents does the project need, and how should they be identified? | At least 10 documents, identified with URLs, subreddit names, file paths, or file descriptions. | Correctly said the project needs at least ten files and that README sources must be locatable. | `02_document_collection.txt`, `01_domain_and_scope.txt`, `03_planning_md_requirements.txt` | Accurate |
| 2 | What chunk size and overlap does this project use, and why? | 900 characters with 180 overlap; preserves short advice thoughts and transitions. | Correctly cited the 900-character target and explained preserving recommendations and transitions. | `04_chunking_strategy.txt`, `02_document_collection.txt`, `06_retrieval_semantic_hybrid.txt` | Accurate |
| 3 | Which embedding model is used, and what top-k value does retrieval use? | `sentence-transformers/all-MiniLM-L6-v2`; top-k is 5. | Correctly gave the embedding model, but the response did not surface the top-k sentence for this combined query. | `06_retrieval_semantic_hybrid.txt`, `03_planning_md_requirements.txt`, `07_grounded_generation.txt` | Partially accurate |
| 4 | What must the system do when a query is not supported by the retrieved documents? | Refuse and say the corpus does not contain enough information instead of guessing. | Correctly said unsupported or low-relevance queries should be refused instead of guessed. | `07_grounded_generation.txt`, `08_query_interface.txt`, `09_evaluation_report.txt` | Accurate |
| 5 | What does the README evaluation report need to include for each of the five test questions? | Question, expected answer, actual response, retrieved chunks, and accuracy judgment. | Correctly stated all five test questions must be documented and each row needs expected answer, actual response, retrieved chunks, and judgment. | `09_evaluation_report.txt`, `03_planning_md_requirements.txt`, `12_rubric_point_traps.txt` | Accurate |

## Failure Case Analysis

**Question that failed:** "Which embedding model is used, and what top-k value does retrieval use?"

**What the system returned:** It cited `sentence-transformers/all-MiniLM-L6-v2`, but did not include "Top-k equals five" in the final answer.

**Root cause:** Retrieval and answer selection split the two parts of the answer. The model sentence lived in the first chunk of `06_retrieval_semantic_hybrid.txt`, while the top-k sentence was in another chunk that ranked lower for the combined query. This is a retrieval-ranking and chunking interaction, not a hallucination.

**Fix:** Either keep the embedding-model and top-k paragraphs in the same chunk for this source, add metadata boosts for same-document follow-up chunks, or use a second targeted retrieval pass when a query asks for multiple named fields.

## Stretch Features

### Hybrid Search

Hybrid search is implemented in `src/rag_pipeline.py` by combining normalized Chroma semantic scores with BM25 scores: `0.65 semantic + 0.35 BM25`.

| Query | Semantic-only top results | Hybrid top results | Better |
|---|---|---|---|
| README retrieval examples and sample chunks | `03`, `09`, `04`, `10`, `03` | `03`, `09`, `12`, `03`, `04` | Hybrid, because BM25 promoted `12_rubric_point_traps.txt`, the exact sample-chunk requirement. |
| BM25 and top-k documents | `06`, `10`, `06`, `01`, `03` | `06`, `06`, `09`, `03`, `03` | Hybrid, because exact terms kept both `06` retrieval chunks near the top. |
| Interface requirements | `08`, then mixed domain/AI usage chunks | `08`, then mixed but still keeps interface first | Tie for first result; hybrid gives a stronger exact-match score. |

### Chunking Strategy Comparison

`python -m src.compare_chunking` compares paragraph-aware 900/180 chunks against fixed 450/50 character chunks on the same queries.

| Query | Paragraph-aware result | Fixed result | Winner |
|---|---|---|---|
| What chunk size and overlap should I use? | `04_chunking_strategy.txt` with the full 900-character recommendation | `02_document_collection.txt` fragment ending "chunk size and overlap" | Paragraph-aware |
| How should unsupported questions be handled? | `03_planning_md_requirements.txt` | `03_planning_md_requirements.txt` | Tie/partial; this BM25-only comparison missed `07_grounded_generation.txt` for both |
| What does AI usage transparency require? | `11_ai_usage_transparency.txt` complete requirement | `11_ai_usage_transparency.txt` complete requirement | Tie |

Paragraph-aware chunking performed better overall because it avoided fragment-only chunks and kept source metadata plus complete recommendations together.

### Metadata Filtering

The CLI supports filtering by metadata category. Without filtering, `What does the interface need to show?` returned `08_query_interface.txt` plus unrelated domain and AI usage chunks. With `--category interface`, it returned only `08_query_interface.txt`, making the result cleaner.

### Conversational Memory

Interactive mode expands follow-up queries with the previous question. Demo:

```text
Question: What does README completeness require?
Answer: The README needs at least five labeled sample chunks... [12_rubric_point_traps.txt]

Question: What about the failure case?
Expanded internally with previous question.
Answer: At least one failure case should be identified honestly. A useful failure explanation ties the problem to a pipeline stage. [09_evaluation_report.txt]
```

## Spec Reflection

The spec helped by forcing the chunk size, overlap, top-k, and evaluation questions to be decided before code. That made implementation easier because each function had a concrete target: load local documents, produce 900/180 chunks, index in Chroma, retrieve top 5, and answer with citations.

The implementation diverged from the original plan by adding a deterministic extractive fallback generator. The plan expected Groq when configured, but a fallback makes the project reproducible without a secret API key and makes grading easier.

## AI Usage

**Instance 1**

- *What I gave the AI:* The assignment instructions, grading rubric, and the planned 900-character/180-overlap chunking strategy.
- *What it produced:* Python code for document loading, metadata parsing, cleaning, chunking, Chroma indexing, retrieval, and CLI querying.
- *What I changed or overrode:* I inspected sample chunks and revised overlap trimming so chunks no longer started mid-word. I also added a deterministic fallback generator because relying only on Groq would make the demo fail without an API key.

**Instance 2**

- *What I gave the AI:* The evaluation plan and rubric items requiring retrieval tests, source attribution, refusal, hybrid search, metadata filtering, and memory.
- *What it produced:* Evaluation commands, README evidence sections, and stretch-feature support code.
- *What I changed or overrode:* I reviewed actual command output and marked the embedding/top-k question partially accurate instead of claiming a perfect result. I tied that failure to retrieval ranking and chunking rather than hiding it.
