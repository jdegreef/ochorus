---
name: book-qa
description: Audit the Ochorus library for content-quality problems — generic or bogus chapter titles, fragmented paragraphs, missing drop-cap letters, running-header noise, front matter leaking in as chapters, empty or tiny chapters. Use when asked to check book/content quality, after a batch import, before adding books to reading plans, or periodically. Produces a findings report; fixes go through the book-import skill (repair) and ship-content-fix (delivery).
---

# Library content QA

Read-only audit: find and rank problems, report, and only fix when asked —
repairs belong to the **book-import** skill, delivery to **ship-content-fix**.

Run from `backend/` with `DJANGO_DEBUG=true uv run python manage.py shell -c` /
a scratch script. The seeded local DB mirrors prod content.

## Automated checks

1. **Generic titles** — chapters whose title is empty or matches
   `^Chapter\s+[\dIVXLC]+\.?$`: the chapterizer failed to capture the real
   heading. (Known cluster: the 6 biography collections — needs
   re-chapterization, not a title clean.)
2. **Duplicate titles within a book** — repeated sub-section headings promoted
   to chapter titles (Ochorus Originals pattern).
3. **Tiny chapters** — `word_count < 150`: front matter, a split heading, or a
   failed merge. Read the body before judging; some prefaces are legitimately
   short.
4. **Giant chapters** — `word_count > 8000`: chapter breaks probably missed.
5. **Fragmented paragraphs** — high `<p>`-count-to-word-count ratio
   (avg words/paragraph < 25): PDF line-break noise the re-merge missed.
6. **Missing drop caps** — body_text starting lowercase or mid-word
   (`^[a-z]` or an obvious truncated first word): image-based drop cap lost.
7. **Running-header noise** — book title or author name appearing repeatedly
   INSIDE body_text.
8. **Mid-sentence chapter splits** — previous chapter's body_text not ending
   in terminal punctuation (`[.!?"'”]$`).
9. **Coverage basics** — books with 0 chapters; chapters with empty
   body_text; missing `body_text` (breaks search); order gaps in a book's
   chapter sequence.

## Report format

Rank by reader impact: (1) broken text mid-reading, (2) wrong/generic titles
(hurts TOC + search + plans), (3) cosmetic. For each finding: book slug,
chapter order, one-line evidence excerpt. End with a fix recommendation per
cluster (which skill handles it) — not one per chapter.

## Known accepted state (don't re-flag)

- `jesus-himself-2` genuinely has 2 chapters (PDF is two addresses).
- Contemporary "Ochorus Originals" have simpler structure than the classics.
