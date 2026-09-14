# Questions & Answers — design & architecture plan

**Status:** proposed (for founder review)
**Author:** drafted with Claude, 2026-09-14
**Scope:** unify "Questions and Answers" (Q&A) content across **Bios (Authors), Sermons,
Books, and Topics**, English-first at high quality, with a clean path to translation.
Articles are explicitly out of scope for now.

> **Naming:** the feature is **"Questions and Answers"** (or **"Q&A"** where space is
> tight) everywhere a reader or the team sees it. It is **never** called "FAQ." The one
> unavoidable exception is invisible: the structured-data type in the JSON-LD is
> `FAQPage` — a fixed schema.org / Google identifier that only search engines read. We
> keep emitting it for the SEO benefit; nothing on the page says FAQ.

---

## 1. Goal

Every major content page — author, sermon, book, topic — should carry a short set of
**answered questions**, grounded strictly in that item's own content:

- **Unique content** on pages that otherwise repeat public-domain text hosted elsewhere.
- **Question-shaped long tail** ("what does X argue about Y", "why is Z important").
- **A clean entity signal** via `FAQPage` JSON-LD.
- **One consistent design, feature set, and architecture** across all four types.
- **English first, at high quality**, then translation into the other languages over time.

> **SEO expectation.** Google restricted FAQ *rich results* to authoritative / gov-health
> sites in 2023. The value here is the **unique, grounded content** and the **entity
> signal**, plus better on-page engagement — **not** a SERP accordion. Frame it that way.

---

## 2. Where we are today (two half-unified implementations)

| Layer | Sermons | Bios (Authors) | Books | Topics |
|---|---|---|---|---|
| Stored field | `study_questions` on the per-language `Sermon` row | `faq` on `Author` + `AuthorTranslation` | — none — | — none — |
| JSON-LD | `faqPage()` (shared, `seo.ts`) | `faqPage()` (shared) | — | — |
| Visible UI | `<dl>` "Questions for reflection" | accordion "Questions" + a **derived** fallback | — | — |
| Translation | not wired | storage exists (`faq_for(lang)`), worker not wired | — | — |
| Coverage (EN) | 93 / 93 ✅ | 29 / 91 | 0 | 0 |

Two things to reconcile before Books and Topics multiply the surface area:

1. **Field name differs** — `study_questions` (sermon) vs `faq` (author).
2. **Visible component differs** — sermon `<dl>` vs bio accordion (with a derived fallback
   the sermon page doesn't have).

The `faqPage()` JSON-LD helper and the `REVIEWED_UI_LOCALES` gating concept are already
shared — good foundations to build the rest on.

---

## 3. Core decision: unify the *contract*, keep storage field-based

**Do not build a polymorphic "Q&A table."** It would fight the fixture-per-work model and
the natural-key seeds, add join complexity, and diverge from how sermons and bios already
work. Instead, keep Q&A as a **field on each content row** and standardize everything
above storage.

### 3.1 One serializer key (the keystone)
Every type exposes its Q&A under the **same API key**, regardless of the underlying field
name:

```json
"qa": [ { "question": "…", "answer": "…" }, … ]
```

The frontend, the JSON-LD, and all tooling then treat all four types identically. This is
what makes "one design across four page types" real without a risky data migration.

### 3.2 One shared component
A single `<QandA>` Svelte component renders the visible section and calls `faqPage()`. It
takes a per-type **display title** as a prop:

- Sermon → **"Questions for reflection"**
- Bio → **"Questions and Answers"** (about the author)
- Book → **"Questions and Answers"** (about the book)
- Topic → **"Questions and Answers"** (about the topic)

Converge the sermon `<dl>` and the bio accordion onto this one component. Recommended
visible form: an **accordion** (expand/collapse) with an **anchor id per question** for
deep-linking, plus the existing "≥ 2 items" floor before it renders at all.

### 3.3 One JSON-LD path
The shared component owns the `faqPage()` call. Keep the helper name as-is (it documents
"this builds the schema.org `FAQPage` blob"), or rename to `qaJsonLd()` if you want zero
"faq" in source — cosmetic, your call. The emitted `@type` stays `FAQPage` either way.

### 3.4 One gating rule
Keep `REVIEWED_UI_LOCALES` + the "≥ 2 items" floor the bio page already uses. Untranslated
locales never show a half-English Q&A block.

### 3.5 One authoring skill
Generalize the `sermon-questions` skill → **`content-questions`**, with a per-type section
(what to read, where it's stored, the reader label).

### Storage stays type-shaped (because translation rides each shape)
The content model already has two storage shapes; Q&A must live where each type's
translations live:

- **Per-language-row types (Sermon, Book):** field on the row. A translated row carries its
  own translated Q&A.
- **Side-table types (Author, Topic):** field on the base row + the `*Translation` table,
  with an `X_for(language)` accessor (bios already do this via `faq_for`).

### The one naming decision that's yours (internal field)
Sermons store `study_questions`; bios store `faq`. **Recommendation: do not rename the
shipped sermon field** (a migration across 93 files for cosmetics). Unify at the serializer
key (`qa`) and map each model's field to it. New types (Book, Topic) adopt **`qa`** as the
stored field name from the start. If you'd rather have one internal name everywhere, do the
sermon rename now — contained but riskier — before three more types entrench the split. The
serializer-key route is the safe default.

---

## 4. Two-tier quality model (editorial + derived)

Generalize the bio page's best idea: **editorial Q&A (hand-authored, high quality) with a
derived fallback built from page facts** when none is written.

- **Editorial** — the goal, and what "full English coverage" means: agent-authored,
  grounded strictly in the source, four answered questions, quoting the text.
- **Derived** — an instant baseline for **entity** pages (bio / book / topic) generated at
  render time from structured facts (author, year, works, topic members) until editorial
  lands, so no page is empty while authoring rolls out.

Sermons went straight to editorial (all 93). Books (~36) and Topics (~10) benefit most from
the derived tier as a floor. The `<QandA>` component reads one array (editorial if present
and ≥ 2, else derived), exactly as the bio page does today.

---

## 5. Authoring & quality (English first)

- **Agent-authored in-session — never via an API key** (standing rule; dev/prod have no
  key). English originals are written the way biographies, articles, quotes, and the sermon
  questions already are.
- **Grounded strictly in each item's own source:** sermon body / book `about` + chapters /
  author bio / topic description + member works.
- **Four question-shaped Q&A per item**, answers verifiably in the source, quoting its own
  phrases. An invented answer is worse than none.
- **Verification pass (new quality feature):** after authoring, a second adversarial read
  that checks each answer is actually supported by the source. Cheap; catches drift. This
  is the one addition over the sermon workflow.
- **Founder reviews the diff before each type scales** (as with sermons).
- **Coverage command:** a `qa_coverage` management command (or a tile on the existing admin
  readiness dashboard) showing per-type English coverage at a glance.
- **Mechanics reused from the sermon work:** byte-stable `render_rows` fixture writer;
  additive-only diffs; `tests_fixture` / `tests_sanitize` / payload tests as the gate; ship
  via `ship-content-fix`.

---

## 6. Translation (later — but design for it now)

Route Q&A through the **existing** AI-translate → native-review pipeline, not a bespoke one:

- Extend each translation worker to translate the Q&A field alongside body / bio, shipping
  `source_type=ai_unreviewed`, promoted only when **the user** runs the `approve_*`
  command. **Never auto-approve.**
- Store translated Q&A where each type's translations already live (per-language row for
  sermon / book; `*Translation` table for author / topic — `faq_for(lang)` is the pattern).
- Reader shows translated Q&A only when reviewed. English is unaffected.

---

## 7. Rollout sequence

- **Phase 0 — contract (small).** Serializer key `qa`; shared `<QandA>` component + per-type
  titles; generalize the skill to `content-questions`; add `qa_coverage`. Converge sermon +
  bio onto the shared component.
- **Phase 1 — plumbing for the missing types.** Book (`qa` field + serializer + component +
  JSON-LD, mirroring the sermon plumbing PR #2330) and Topic (`qa` on `Topic` +
  `TopicTranslation` + serializer + render). Additive migrations, low risk.
- **Phase 2 — English coverage.** Finish bios (~62), then books (~36), then topics (~10);
  sermons already done. Derived fallback gives entity pages an immediate floor.
- **Phase 3 — translation.** Extend the workers per type, per language, through the existing
  review gate.

### Effort / risk notes
- Plumbing per type ≈ one focused PR each (the #2330 shape).
- Authoring is the bulk of the work — **books especially** (long, multi-chapter texts;
  expect to source from `about` + chapter titles + key chapters, or lean on the derived
  tier plus a few editorial to start).
- New fields are additive `JSONField(default=list)` migrations — low risk. The only risky
  option is renaming the shipped sermon field, which this plan avoids.

---

## 8. Open questions for the founder

1. **Order:** Books first (biggest gap, needs plumbing) or finish Bios first (no plumbing,
   immediate wins)? Recommendation: finish Bios, then Books, then Topics.
2. **Internal field name:** accept the serializer-key approach (keep `study_questions` /
   `faq` as stored names), or do the one-time sermon rename to make everything `qa`?
3. **Derived tier:** enable the auto-from-facts baseline on Books and Topics, or ship only
   editorial there?
4. **Helper rename:** leave `faqPage()` as-is, or rename to `qaJsonLd()` for zero "faq" in
   source?
