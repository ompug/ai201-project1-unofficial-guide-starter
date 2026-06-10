# The Unofficial Guide - CodePath AI201 Project 1

For this assignment I built a small RAG system that acts like an unofficial survival guide for CodePath AI201 Project 1. I chose this domain because the assignment is not conceptually hard to read, but it has a lot of small requirements spread across the milestone instructions and rubric. A student could easily miss things like sample chunks, retrieval examples, refusal behavior, source citations, or AI usage transparency.

My goal was to make those requirements searchable. A user can ask a normal question like "What does the README evaluation report need?" and the system retrieves relevant chunks from my local guide documents, then answers with citations.

## How to Run the Project

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.rag_pipeline --reindex --inspect-chunks
python -m src.query "What chunk size and overlap does this project use?" --mode hybrid --show-chunks
python -m src.evaluate
```

The project can use Groq if a `GROQ_API_KEY` is added to `.env`, but I also wrote a deterministic fallback answerer. That way the project still works without an API key, which made it easier to test and demo.

## Domain

The domain is an unofficial student guide for completing CodePath AI201 Project 1. This kind of knowledge is valuable because official assignment text tells you what to do, but it does not always highlight which small details students are most likely to forget. I wrote the documents as practical student notes covering planning, document collection, chunking, retrieval, grounded generation, evaluation, stretch features, and README expectations.

## Document Sources

I used local text files as the source documents so the project is reproducible and does not depend on fragile scraping. Each file has metadata at the top (`Title`, `Source`, `Date`, `Category`, and `Rating`) and then the actual document text.

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

The ingestion code is in `src/rag_pipeline.py`. It loads all `.txt` files from `documents/raw/`, parses their metadata, cleans the body text, and keeps metadata attached to every chunk. The cleaning step handles extra whitespace, HTML-looking tags, and common page-noise phrases. Since my source files are already plain text, I did not need PDF extraction or browser scraping.

The final pipeline produced **18 chunks from 12 documents**.

**Chunk size:** 900 characters  
**Overlap:** 180 characters

I chose 900 characters because these documents are short advice-style notes, not long textbook chapters. Most useful answers fit in one to three paragraphs, so this chunk size usually keeps the whole idea together. I used 180 characters of overlap because a requirement and its explanation sometimes land near a paragraph boundary. The overlap reduces the chance that retrieval gets only half of the useful context.

The chunker tries to preserve paragraph boundaries first. I inspected the printed chunks after indexing and adjusted the overlap logic because my first version sometimes started a chunk in the middle of a word.

### Five Sample Chunks

1. Source: `01_domain_and_scope.txt`  
   Sample: "For this project, the domain is an unofficial student survival guide for CodePath AI201 Project 1... students can miss small scoring details such as sample chunks, out-of-scope refusal, and production embedding tradeoffs."

2. Source: `02_document_collection.txt`  
   Sample: "The project needs at least ten specific documents, pages, threads, or files. The README should name the domain and identify the sources clearly enough that another person could locate them."

3. Source: `03_planning_md_requirements.txt`  
   Sample: "`planning.md` should be completed before pipeline code. It needs substantive sections for Domain, Documents, Chunking Strategy, Retrieval Approach, Evaluation Plan, Anticipated Challenges, Architecture, and AI Tool Plan."

4. Source: `04_chunking_strategy.txt`  
   Sample: "A target of about 900 characters works well for these documents because most important points fit in one to three paragraphs."

5. Source: `07_grounded_generation.txt`  
   Sample: "The system prompt should explicitly say that if the answer is not supported by the retrieved context, the assistant must refuse and say the corpus does not contain enough information."

## Retrieval

I used `sentence-transformers/all-MiniLM-L6-v2` for embeddings and ChromaDB as the local vector store. The default retrieval value is **top-k = 5**.

I picked `all-MiniLM-L6-v2` because it is free, local, fast, and good enough for a small English-only corpus. If I were choosing a production model, I would compare accuracy, context length, multilingual support, latency, privacy, cost, and whether the model handles messy student wording well. A larger hosted model might retrieve better results for ambiguous questions, but it would also add API cost and external-service dependency.

I also implemented hybrid search as a stretch feature. Hybrid mode combines semantic similarity from Chroma with BM25 keyword search:

```text
hybrid score = 0.65 * semantic score + 0.35 * BM25 score
```

This helped with exact rubric terms like `planning.md`, `top-k`, `sample chunks`, and `BM25`.

### Retrieval Test Examples

| Query | Top returned chunks | My relevance check |
|---|---|---|
| "How many retrieval examples and sample chunks does the README need?" | `03_planning_md_requirements.txt`, `09_evaluation_report.txt`, `12_rubric_point_traps.txt` | These are relevant because they mention the required retrieval examples and the five labeled sample chunks. `12_rubric_point_traps.txt` is especially useful because it directly lists the easy-to-miss README items. |
| "What does the interface need to show?" | `08_query_interface.txt`, `01_domain_and_scope.txt`, `11_ai_usage_transparency.txt` | The top result is the right one because it explains the CLI fields and sample transcript requirement. The other results are less direct, but still connected to demo/report expectations. |
| "What AI usage transparency is required?" | `11_ai_usage_transparency.txt`, `02_document_collection.txt`, `03_planning_md_requirements.txt` | The first result is clearly relevant because it says the AI Usage section needs at least two concrete instances and must explain what I reviewed or changed. |

## Grounded Generation

I enforce grounding in the prompt and in the pipeline. The prompt instruction is:

```text
You answer only from the retrieved context. If the answer is not supported, refuse and say the corpus does not contain enough information. Cite source file names in brackets after every factual claim.
```

If Groq is available, the retrieved chunks are sent as context with that instruction. If Groq is not available, the fallback answerer only extracts sentences from retrieved chunks and adds source filenames after them. This is less fluent than a full LLM answer, but it makes the output easy to audit.

Example system response 1:

> The project needs at least ten specific documents, pages, threads, or files. [02_document_collection.txt] The README should name the domain and identify the sources clearly enough that another person could locate them. [02_document_collection.txt]

Example system response 2:

> The AI Usage section should describe at least two specific instances of AI tool use. [11_ai_usage_transparency.txt] Each instance should say what the student directed the tool to do, what input was provided, what output was produced, and what the student reviewed, revised, or overrode. [11_ai_usage_transparency.txt]

Out-of-scope example:

> Query: What is the housing deposit deadline for UCLA?  
> Response: I do not have enough information in the AI201 Project 1 guide corpus to answer that. The retrieved guide only covers AI201 Project 1 requirements, so answering a campus housing deadline would require unsupported outside knowledge.

## Query Interface

The query interface is a command-line tool in `src/query.py`.

Inputs:

- Question text
- `--mode semantic` or `--mode hybrid`
- `--top-k`
- `--category` for metadata filtering
- `--show-chunks` to print retrieved chunks
- `--interactive` for a simple memory mode

Outputs:

- Original question
- Retrieval mode
- Grounded answer with source citations
- Retrieved chunks, scores, and source metadata when `--show-chunks` is used

Sample interaction:

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

I used the five questions from `planning.md` and ran them through the system with hybrid search.

| # | Question | Expected correct answer | System response summary | Retrieved chunks | Accuracy |
|---|----------|-------------------------|-------------------------|------------------|----------|
| 1 | How many source documents does the project need, and how should they be identified? | At least 10 documents, identified with URLs, subreddit names, file paths, or file descriptions. | It correctly said the project needs at least ten source documents/files and that README sources should be locatable. | `02_document_collection.txt`, `01_domain_and_scope.txt`, `03_planning_md_requirements.txt` | Accurate |
| 2 | What chunk size and overlap does this project use, and why? | 900 characters with 180 overlap; this keeps short advice thoughts together and protects transitions. | It correctly cited the 900-character chunk target and explained why overlap helps near paragraph boundaries. | `04_chunking_strategy.txt`, `02_document_collection.txt`, `06_retrieval_semantic_hybrid.txt` | Accurate |
| 3 | Which embedding model is used, and what top-k value does retrieval use? | `sentence-transformers/all-MiniLM-L6-v2`; top-k is 5. | It clearly returned the embedding model, but the final answer did not surface the top-k sentence even though a relevant retrieval document existed. | `06_retrieval_semantic_hybrid.txt`, `03_planning_md_requirements.txt`, `07_grounded_generation.txt` | Partially accurate |
| 4 | What must the system do when a query is not supported by the retrieved documents? | Refuse and say the corpus does not contain enough information instead of guessing. | It correctly said unsupported or low-relevance queries should be refused instead of guessed. | `07_grounded_generation.txt`, `08_query_interface.txt`, `09_evaluation_report.txt` | Accurate |
| 5 | What does the README evaluation report need to include for each of the five test questions? | The question, expected answer, actual response, retrieved chunks, and an accuracy judgment. | It correctly stated that all five questions must be documented and that each row needs expected answer, actual response, retrieved chunks, and judgment. | `09_evaluation_report.txt`, `03_planning_md_requirements.txt`, `12_rubric_point_traps.txt` | Accurate |

## Failure Case Analysis

The main failure case was question 3:

> Which embedding model is used, and what top-k value does retrieval use?

The system returned the embedding model correctly, but it did not include the top-k value in the final response. I traced this to retrieval and answer selection. The embedding model sentence and the top-k sentence are in related retrieval content, but the answerer selected the model sentence and some nearby citation/architecture content before it selected the exact "top-k equals five" sentence.

This is not a hallucination problem. It is a ranking/chunk-selection problem. To fix it, I would either keep the embedding-model and top-k details in the same chunk, add a same-document boost when multiple chunks from one source are relevant, or do a second retrieval pass for named fields like "model" and "top-k."

## Stretch Features

### Hybrid Search

Hybrid search is implemented in `src/rag_pipeline.py`. It combines normalized semantic scores and BM25 scores. I compared semantic-only and hybrid results on three queries:

| Query | Semantic-only top results | Hybrid top results | Which was better |
|---|---|---|---|
| README retrieval examples and sample chunks | `03`, `09`, `04`, `10`, `03` | `03`, `09`, `12`, `03`, `04` | Hybrid was better because BM25 promoted `12_rubric_point_traps.txt`, which directly mentions the sample-chunk requirement. |
| BM25 and top-k documents | `06`, `10`, `06`, `01`, `03` | `06`, `06`, `09`, `03`, `03` | Hybrid was better because exact terms kept the retrieval document near the top. |
| Interface requirements | `08`, then mixed results | `08`, then mixed results | Tie for the top result, but hybrid gave the exact interface chunk a stronger score. |

### Chunking Strategy Comparison

I added `src/compare_chunking.py` to compare my paragraph-aware 900/180 chunks with a fixed 450/50 character strategy.

| Query | Paragraph-aware result | Fixed-character result | Winner |
|---|---|---|---|
| What chunk size and overlap should I use? | `04_chunking_strategy.txt` with the full chunking recommendation | `02_document_collection.txt` fragment ending in "chunk size and overlap" | Paragraph-aware |
| How should unsupported questions be handled? | `03_planning_md_requirements.txt` | `03_planning_md_requirements.txt` | Tie/partial miss for both |
| What does AI usage transparency require? | `11_ai_usage_transparency.txt` complete requirement | `11_ai_usage_transparency.txt` complete requirement | Tie |

The paragraph-aware version was better overall because it avoided fragment-only chunks and kept complete recommendations together.

### Metadata Filtering

The CLI supports metadata filtering with `--category`. For example:

```bash
python -m src.query "What does the interface need to show?" --mode hybrid --category interface --show-chunks
```

Without the filter, the query returns the interface document plus some less related domain/reflection chunks. With `--category interface`, it returns only `08_query_interface.txt`, which makes the result cleaner.

### Conversational Memory

Interactive mode keeps the previous question and appends it to the next query. This lets a follow-up question use previous context.

Example:

```text
Question: What does README completeness require?
Answer: The README needs at least five labeled sample chunks... [12_rubric_point_traps.txt]

Question: What about the failure case?
Answer: At least one failure case should be identified honestly. A useful failure explanation ties the problem to a pipeline stage. [09_evaluation_report.txt]
```

## Spec Reflection

Writing `planning.md` first helped more than I expected. It forced me to make decisions about the domain, chunk size, overlap, top-k, and evaluation questions before coding, so I had something concrete to test against.

One place I diverged from the original plan was generation. I planned around Groq, but I added a deterministic fallback answerer because I did not want the project to fail if no API key was available. The fallback is not as polished as an LLM response, but it is transparent and easy to grade because every sentence comes from retrieved chunks.

## AI Usage

**Instance 1**

- *What I gave the AI:* I gave Codex the assignment instructions, rubric, and my chunking plan with 900-character chunks and 180-character overlap.
- *What it produced:* It helped draft the ingestion/chunking code, including metadata parsing and Chroma indexing.
- *What I reviewed or changed:* I ran the chunk inspection command myself and noticed some overlap text started mid-word. I changed the overlap trimming logic so chunks started more cleanly. I also checked that the final chunk count and sample chunks made sense.

**Instance 2**

- *What I gave the AI:* I gave Codex the retrieval, grounded generation, evaluation, and stretch-feature requirements from the rubric.
- *What it produced:* It helped create the CLI, evaluation script, hybrid search comparison, and README structure.
- *What I reviewed or changed:* I ran the actual evaluation commands and did not mark everything perfect. I kept the embedding/top-k question as partially accurate because the system missed part of the answer. I also wrote the failure analysis around the real retrieval behavior instead of hiding that issue.
