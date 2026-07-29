# NCB structural chunk example

## Why plain extraction fails

The consolidated PDF has superscript amendment-note numbers adjacent to headings. Plain text can produce:

- `มาตรา ๒๑` although the legal section is `มาตรา ๒` plus footnote `๑`;
- `มาตรา ๒๔/๑๑๙` although the section is `มาตรา ๒๔/๑` plus footnote `๑๙`;
- amendment-history notes at the page bottom appended to the active section;
- a page-continuation cross-reference beginning with `มาตรา ...` and being mistaken for a new section.

Resolve these with layout blocks, sequential section logic, canonical metadata, and a separate historical appendix corpus.

## Good chunk

```yaml
law_name: พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต พ.ศ. ๒๕๔๕ (รวมฉบับแก้ไข ๑-๖)
section_id: "17"
section_heading: มาตรา ๑๗
topic: หมวด ๓ สิทธิและหน้าที่ของบริษัทข้อมูลเครดิต สมาชิกและผู้ใช้บริการ
page_start: 6
page_end: 6
structural_path:
  - พระราชบัญญัติการประกอบธุรกิจข้อมูลเครดิต...
  - หมวด ๓...
  - มาตรา ๑๗
```

The body contains the full security, correction, access-log, and destruction requirements but excludes amendment footnotes.

## Retrieval example

Question:

> IT Internal Audit ควรตรวจหลักฐานใดเกี่ยวกับการเข้าถึงข้อมูล NCB และต้องเก็บ log นานเท่าใด

Expected route:

1. BM25 matches `เข้าถึง`, `บันทึก`, `สองปี`.
2. Embedding retrieves section 17 and close neighbours.
3. Reranker retains section 17 and rejects disclosure/oversight sections.
4. Generator receives the complete section 17 with page 6.
5. Citation validator accepts only section `17`.

Bad route: inject raw dense top-k candidates and ask the model to choose. In the measured NCB test, exact-section echo achieved 100% relevant citation precision/recall, while dense top-4 averaged 40% relevant precision and 66.7% recall.
