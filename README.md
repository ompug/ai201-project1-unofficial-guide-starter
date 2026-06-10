# The Unofficial Guide - Highly Acclaimed Must-Watch Anime

For this project I built a RAG system that works like an unofficial recommendation guide for highly acclaimed must-watch anime. The goal is not just to list popular titles, but to answer questions like "What should I watch for cyberpunk?" or "What is a good gateway anime movie?" with grounded recommendations and visible source citations.

I chose this domain because anime recommendations are everywhere, but they are often either giant ranked lists with no context or fan threads that assume you already know the classics. I wanted a small guide that explains *why* a title fits a viewer's mood, genre preference, or tolerance for heavier material.

## How to Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
rm -rf chroma_db
python -m src.rag_pipeline --reindex --inspect-chunks
python -m src.query "What should I watch for cyberpunk and landmark animation?" --mode hybrid --show-chunks
python -m src.evaluate
```

If `GROQ_API_KEY` is set in `.env`, the project can call Groq. I also kept a deterministic fallback answerer so the project still works without an API key.

## Document Sources

I used local text files for the actual corpus, but each file is based on specific outside sources. I paraphrased the source material into recommendation notes instead of scraping full pages.

| # | Source document | Type | Source URL(s) or file path |
|---|---|---|---|
| 1 | Spirited Away gateway film notes | Movie recommendation note | `documents/raw/01_spirited_away_gateway.txt`; Rotten Tomatoes anime movies guide: https://editorial.rottentomatoes.com/guide/best-anime-movies/; BFI key anime films: https://www.bfi.org.uk/sight-and-sound/lists/50-key-anime-films |
| 2 | Cowboy Bebop series notes | Series recommendation note | `documents/raw/02_cowboy_bebop_series.txt`; Rotten Tomatoes: https://www.rottentomatoes.com/tv/cowboy_bebop/s01; IMDb: https://www.imdb.com/title/tt0213338/ |
| 3 | Fullmetal Alchemist: Brotherhood notes | Series recommendation note | `documents/raw/03_fullmetal_alchemist_brotherhood.txt`; MyAnimeList: https://myanimelist.net/anime/5114/Fullmetal_Alchemist__Brotherhood; IMDb: https://www.imdb.com/title/tt1355642/ |
| 4 | Frieren: Beyond Journey's End notes | Series recommendation note | `documents/raw/04_frieren_modern_fantasy.txt`; MyAnimeList: https://myanimelist.net/anime/52991/Sousou_no_Frieren; Decider: https://decider.com/what-to-watch/frieren-beyond-journeys-end/ |
| 5 | Steins;Gate notes | Series recommendation note | `documents/raw/05_steins_gate_sci_fi.txt`; MyAnimeList: https://myanimelist.net/anime/9253/Steins_Gate; IMDb: https://www.imdb.com/title/tt1910272/ |
| 6 | Neon Genesis Evangelion notes | Series recommendation note | `documents/raw/06_evangelion_psychological_mecha.txt`; BFI: https://www.bfi.org.uk/features/neon-genesis-evangelion; Netflix: https://www.netflix.com/title/81033445 |
| 7 | Akira notes | Movie recommendation note | `documents/raw/07_akira_cyberpunk_film.txt`; Rotten Tomatoes: https://www.rottentomatoes.com/m/akira; BFI key anime films: https://www.bfi.org.uk/sight-and-sound/lists/50-key-anime-films |
| 8 | Grave of the Fireflies notes | Movie recommendation note | `documents/raw/08_grave_of_the_fireflies.txt`; Rotten Tomatoes anime movies guide: https://editorial.rottentomatoes.com/guide/best-anime-movies/; BFI key anime films: https://www.bfi.org.uk/sight-and-sound/lists/50-key-anime-films |
| 9 | Attack on Titan notes | Series recommendation note | `documents/raw/09_attack_on_titan_dark_action.txt`; Crunchyroll news: https://www.crunchyroll.com/news/latest/2020/12/14/attack-on-titan-final-season-is-myanimelists-biggest-premiere-ever; IMDb: https://www.imdb.com/title/tt2560140/ |
| 10 | Your Name notes | Movie recommendation note | `documents/raw/10_your_name_romance_gateway.txt`; Rotten Tomatoes anime movies guide: https://editorial.rottentomatoes.com/guide/best-anime-movies/; IMDb: https://www.imdb.com/title/tt5311514/ |
| 11 | Mob Psycho 100 notes | Series recommendation note | `documents/raw/11_mob_psycho_character_growth.txt`; MyAnimeList: https://myanimelist.net/anime/32182/Mob_Psycho_100; IMDb: https://www.imdb.com/title/tt5897304/ |
| 12 | Watch matching synthesis guide | Cross-title guide | `documents/raw/12_watch_order_and_matching.txt`; synthesis based on the other eleven source notes |

## Document Pipeline

The ingestion code is in `src/rag_pipeline.py`. It loads every `.txt` file in `documents/raw/`, parses metadata fields (`Title`, `Source`, `Date`, `Category`, `Rating`), cleans the text, and keeps the metadata attached to each chunk.

The final index has **12 documents and 13 chunks**.

**Chunk size:** 1000 characters  
**Overlap:** 160 characters

I changed the chunking strategy after pivoting the topic. The anime documents are recommendation cards with three short sections: why the title is acclaimed, what source context supports it, and when I would or would not recommend it. A 1000-character chunk usually keeps one full anime card together. The 160-character overlap helps when the source evidence and recommendation note land near a boundary.

### Five Sample Chunks

1. Source: `01_spirited_away_gateway.txt`  
   Sample: "Spirited Away is one of the safest first recommendations for someone who wants to understand why anime is taken seriously as cinema."

2. Source: `03_fullmetal_alchemist_brotherhood.txt`  
   Sample: "Fullmetal Alchemist: Brotherhood is the main recommendation when someone wants a complete, widely loved adventure series with action, comedy, tragedy, politics, and moral questions."

3. Source: `04_frieren_modern_fantasy.txt`  
   Sample: "Frieren: Beyond Journey's End is the modern fantasy recommendation for viewers who want emotion, atmosphere, and patience more than constant fights."

4. Source: `07_akira_cyberpunk_film.txt`  
   Sample: "Akira is the must-watch film for viewers asking why anime became globally associated with cyberpunk, motorcycles, body horror, psychic power, and adult animation."

5. Source: `08_grave_of_the_fireflies.txt`  
   Sample: "Grave of the Fireflies is highly acclaimed, but it should be recommended with care."

## Retrieval

**Embedding model:** `sentence-transformers/all-MiniLM-L6-v2`  
**Vector store:** ChromaDB  
**Top-k:** 5  
**Default mode:** hybrid search

I chose `all-MiniLM-L6-v2` because it runs locally, is free, and is fast enough for a small English-language recommendation corpus. For a production anime recommender, I would compare models on fuzzy taste queries, Japanese/romanized title handling, multilingual support, latency, privacy, and cost. I would especially test whether a stronger model understands subjective phrases like "bittersweet," "cozy," "psychological," or "emotionally devastating."

Hybrid search combines semantic similarity with BM25 keyword scoring:

```text
hybrid score = 0.65 * semantic score + 0.35 * BM25 score
```

This helps when a query has exact title words like `Steins Gate`, `Akira`, or `Mob Psycho 100`, while semantic search still helps for mood-based wording like "gateway anime" or "sad war movie."

### Retrieval Test Examples

| Query | Top returned chunks | Why the chunks are relevant |
|---|---|---|
| "What should I watch for cyberpunk and landmark animation?" | `07_akira_cyberpunk_film.txt`, `12_watch_order_and_matching.txt`, `11_mob_psycho_character_growth.txt` | The top result is exactly right because the Akira note mentions cyberpunk, landmark animation, and darker sci-fi. The matching guide also supports Akira as the cyberpunk/history pick. |
| "Steins Gate time travel payoff" | `05_steins_gate_sci_fi.txt`, `12_watch_order_and_matching.txt`, `04_frieren_modern_fantasy.txt` | The top chunk is relevant because it identifies Steins;Gate as the time-travel sci-fi pick and explains the slow-start/strong-payoff structure. |
| "What movie should I watch for romance and polished visuals?" | `10_your_name_romance_gateway.txt`, `12_watch_order_and_matching.txt`, `08_grave_of_the_fireflies.txt` | The first result is relevant because it directly recommends Your Name for romance, emotion, and a polished modern look. |

## Grounded Generation

The generation step is grounded by both prompt rules and pipeline structure. The prompt says:

```text
You answer only from the retrieved context. If the answer is not supported, refuse and say the corpus does not contain enough information. Cite source file names in brackets after every factual claim.
```

If Groq is not configured, the fallback answerer extracts sentences only from retrieved chunks. This makes the answer less conversational, but it keeps every claim tied to a visible source.

Example response 1:

> Akira is the must-watch film for viewers asking why anime became globally associated with cyberpunk, motorcycles, body horror, psychic power, and adult animation. [07_akira_cyberpunk_film.txt] Recommendation note: use Akira for viewers asking for influential sci-fi, cyberpunk, landmark animation, or darker movies. [07_akira_cyberpunk_film.txt]

Example response 2:

> Your Name is a strong gateway anime film for viewers who want romance, emotion, and a polished modern look. [10_your_name_romance_gateway.txt] Recommendation note: use Your Name for viewers asking for a modern anime movie, romance, beautiful visuals, or something accessible after Spirited Away. [10_your_name_romance_gateway.txt]

Out-of-scope refusal:

> Query: Where can I stream Cowboy Bebop in Brazil tonight?  
> Response: I do not have enough information in the must-watch anime guide corpus to answer that. The guide covers recommendation fit and acclaim, not current streaming availability, prices, or future release schedules.

## Query Interface

The interface is a Linux-friendly CLI in `src/query.py`.

Inputs:

- Question text
- `--mode semantic` or `--mode hybrid`
- `--top-k`
- `--category` for metadata filtering, such as `movie`, `series`, or `guide`
- `--show-chunks`
- `--interactive` for a simple memory mode

Outputs:

- Question
- Retrieval mode
- Grounded answer with source citations
- Retrieved chunks, source files, titles, and scores when `--show-chunks` is used

Sample interaction:

```text
$ python -m src.query "What should I watch for cyberpunk and landmark animation?" --mode hybrid --show-chunks
Question: What should I watch for cyberpunk and landmark animation?
Mode: hybrid
Answer:
Akira is the must-watch film for viewers asking why anime became globally associated with cyberpunk, motorcycles, body horror, psychic power, and adult animation. [07_akira_cyberpunk_film.txt]

Retrieved chunks:
1. 07_akira_cyberpunk_film.txt | Must-Watch Anime Notes - Akira for Cyberpunk Impact and Animation | score=1.000 ...
```

## Evaluation Report

I ran the five questions from `planning.md` through hybrid search.

| # | Question | Expected correct answer | System response summary | Retrieved chunks | Accuracy |
|---|---|---|---|---|---|
| 1 | What is a good gateway anime movie for someone new to anime? | Spirited Away; Your Name is also a good modern accessible option. | It answered with Spirited Away and Your Name from the matching guide, then cited the Your Name note. It also pulled in one weaker Akira chunk. | `12_watch_order_and_matching.txt`, `10_your_name_romance_gateway.txt`, `07_akira_cyberpunk_film.txt` | Accurate |
| 2 | Which anime should I watch for cyberpunk and landmark animation? | Akira. | It correctly recommended Akira and cited both the Akira source note and the matching guide. | `07_akira_cyberpunk_film.txt`, `12_watch_order_and_matching.txt`, `11_mob_psycho_character_growth.txt` | Accurate |
| 3 | What should I watch if I want a complete adventure series with a strong ending? | Fullmetal Alchemist: Brotherhood. | It correctly surfaced Brotherhood from both the matching guide and the Brotherhood-specific source note. | `12_watch_order_and_matching.txt`, `03_fullmetal_alchemist_brotherhood.txt`, `12_watch_order_and_matching.txt` | Accurate |
| 4 | Which recommendation fits a recent thoughtful fantasy about memory and grief? | Frieren: Beyond Journey's End. | It correctly recommended Frieren and cited the Frieren note, but also retrieved Grave of the Fireflies because of shared emotional/grief wording. | `04_frieren_modern_fantasy.txt`, `08_grave_of_the_fireflies.txt`, `12_watch_order_and_matching.txt` | Accurate |
| 5 | What anime should I avoid recommending as a casual comfort watch because it is emotionally devastating? | Grave of the Fireflies. | It correctly recommended caution around Grave of the Fireflies and cited the emotional war drama note. | `08_grave_of_the_fireflies.txt`, `12_watch_order_and_matching.txt`, `09_attack_on_titan_dark_action.txt` | Accurate |

## Failure Case Analysis

**Question that failed:** "What is a great mecha anime?"

**What the system returned:** It returned Your Name, Cowboy Bebop, and Akira chunks instead of Neon Genesis Evangelion.

**Root cause:** This is a retrieval failure. The Evangelion document contains the word "mecha," but the query is very short and generic. Semantic similarity over-weighted broad "anime recommendation" language, and BM25 did not boost the Evangelion chunk enough to overcome those broader matches.

**What I would change:** I would add a small synonym/metadata layer for genres, such as mapping `mecha` directly to documents tagged `mecha`, or add a structured `subgenre` metadata field separate from the broad `series` category. I could also add more repeated genre terms in the Evangelion note so exact keyword search has a stronger signal.

## Stretch Features

### Hybrid Search

Hybrid search is implemented in `src/rag_pipeline.py`. On the query `Steins Gate time travel payoff`, semantic search already returned `05_steins_gate_sci_fi.txt` first, but hybrid search improved the result by giving the exact Steins;Gate chunk a stronger score and keeping the final answer focused on only that source.

| Query | Semantic-only top result | Hybrid top result | Which was better |
|---|---|---|---|
| Steins Gate time travel payoff | `05_steins_gate_sci_fi.txt`, score 0.720 | `05_steins_gate_sci_fi.txt`, score 1.000 | Hybrid, because exact title and time-travel terms made the result more confident and cleaner. |
| Cyberpunk and landmark animation | `07_akira_cyberpunk_film.txt` | `07_akira_cyberpunk_film.txt` | Tie for rank, but hybrid strengthened the exact cyberpunk match. |
| Romance and polished visuals | `10_your_name_romance_gateway.txt` | `10_your_name_romance_gateway.txt` | Tie for rank, with hybrid preserving the right movie-first answer. |

### Chunking Strategy Comparison

I compared paragraph-aware 1000/160 chunks against fixed 450/50 character chunks with:

```bash
python -m src.compare_chunking
```

| Query | Paragraph-aware result | Fixed-character result | Winner |
|---|---|---|---|
| Cyberpunk and landmark animation | `07_akira_cyberpunk_film.txt` with the full Akira recommendation | `07_akira_cyberpunk_film.txt`, but starting mid-document | Paragraph-aware |
| Gateway anime movie | `10_your_name_romance_gateway.txt` with a complete recommendation | `10_your_name_romance_gateway.txt`, but starting in the middle of the source-evidence paragraph | Paragraph-aware |
| Emotionally devastating comfort watch | The comparison struggled and returned `01_spirited_away_gateway.txt` for both strategies | Same wrong source | Neither; this exposed a retrieval weakness for that wording |

Paragraph-aware chunking performed better overall because the returned chunks were readable recommendation cards instead of fragments, even when the top source was the same.

### Metadata Filtering

The CLI supports metadata filtering. This command filters to movies only:

```bash
python -m src.query "What movie should I watch for romance and polished visuals?" --mode hybrid --category movie --show-chunks
```

With the filter, the top answer is `10_your_name_romance_gateway.txt` and the retrieved set only contains movie documents. Without the filter, the same query can include the general matching guide and other related titles.

### Conversational Memory

Interactive mode expands the second query with the previous question. Example:

```text
Question: I want a gateway anime movie.
Answer: The safest gateway path is Spirited Away or Your Name for a movie... [12_watch_order_and_matching.txt]

Question: What about something more romantic?
Answer: Your Name is a strong gateway anime film for viewers who want romance, emotion, and a polished modern look. [10_your_name_romance_gateway.txt]
```

## Spec Reflection

Writing `planning.md` helped because the anime domain needed clearer evaluation questions than the original project topic. I had to decide whether questions would be title-based, genre-based, or mood-based before changing the code. That made it easier to tell whether retrieval was actually working.

One divergence from the plan is that the fallback answerer is still extractive and sometimes includes a nearby weaker chunk. I kept it because it is transparent and works without an API key, but a production version would use a stronger generator and better reranking.

## AI Usage

**Instance 1**

- *What I gave the AI:* I asked Codex to pivot the existing project from an assignment guide to highly acclaimed must-watch anime, while keeping the rubric requirements.
- *What it produced:* It helped create the new source document set, update `planning.md`, and adjust the pipeline constants and refusal behavior.
- *What I reviewed or changed:* I checked the source list, made sure the documents were specific and locatable, and verified the new chunk count after reindexing.

**Instance 2**

- *What I gave the AI:* I gave Codex the new anime evaluation questions and asked it to run retrieval/evaluation tests.
- *What it produced:* It helped update `src/evaluate.py`, gather CLI outputs, and write the README evaluation/failure sections.
- *What I reviewed or changed:* I kept the mecha query as an honest failure case instead of tuning it away, because it showed a real retrieval weakness tied to genre wording and ranking.
