# Glossary coverage: manual check of 30 candidates

Candidates are evaluation questions whose own hint has a definition with cosine
similarity >= 0.85 (bge-small) to an entry of the glossary built from the *other*
half (71.4% of the 500 questions; only 30.4% have *all* of their definitions
matched). A random sample of 30 candidates (seed 0) was labelled by reading
each (own definition, closest glossary entry) pair.

Labelled by Claude (the AI assistant that built the project), not by a human
annotator; the sample and pairs are in `glossary_coverage_rows.json` for re-checking.

| Label | Meaning | Count | Questions (sample index) |
|---|---|---|---|
| Exact | the glossary states the same definition | 16 | 1, 2, 4, 5, 6, 7, 10, 13, 15, 16, 17, 20, 21, 25, 26, 27 |
| Template | same rule pattern with another constant (e.g. "TR010 is the molecule id") | 7 | 0, 9, 14, 18, 19, 23, 24 |
| Partial | names the right column but not the needed rule | 5 | 3, 8, 11, 22, 29 |
| Misleading | a conflicting definition for the same term | 2 | 12 (tallest = rank 1 vs MAX(height)), 28 (originalType vs types) |

Useful (exact + template): 23/30 = 77% of candidates, so roughly
0.714 x 0.77 = about 55% of evaluation questions have a usable definition in the
glossary. This is the ceiling for RQ1: retrieval cannot find a definition nobody wrote down.
