# Structural legal chunk quality gates

## Required deterministic checks

| Gate | Target |
|---|---:|
| Non-empty chunks | 100% |
| Valid page anchors | 100% |
| Content hash present | 100% |
| Active section id unique | 100% |
| Content begins with canonical heading | 100% |
| Structural path present | 100% |
| Footnote-only chunks | 0 |
| Descending section references classified as headings | 0 |
| Chapter titles with fused footnote markers | 0 after canonical review |
| Page-anchored retrieval evidence | 100% of evaluation questions |

## Manual samples

Inspect the source page and extracted body for:

1. first and last active sections;
2. the longest section;
3. a section spanning pages;
4. a slash section such as `20/1` or `24/3`;
5. a page with several amendment footnotes;
6. a page where a cross-reference begins a new line;
7. a section containing exceptions or deadlines.

## Failure routing

- Wrong or missing page: repair page/block ordering.
- Heading id includes a footnote number: canonicalize the heading using sequence and font/layout evidence.
- Chapter title ends with a fused marker such as `สินเชื่อ๑๘`: compare the
  rendered heading, then store a canonical title without the note number.
- Historical note appears in body: filter its page block, not a global text phrase.
- Cross-reference became a new chunk: require monotonic section order or stronger heading-layout evidence.
- Relevant section absent from retrieval: fix indexing/query routing before prompting.
- Correct evidence but incomplete answer: fix synthesis prompt or output budget.
- Model cites every supplied candidate: add reranking and post-generation relevance checks.
