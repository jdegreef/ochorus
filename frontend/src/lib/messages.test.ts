import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
// Terms deliberately identical to English — shared with the catalogue summary.
import { SAME_AS_ENGLISH_OK } from "../../scripts/same-as-english.mjs";

/**
 * i18n completeness guard. Keeps the four locales honest so a missing key or a
 * left-behind English string can't ship silently:
 *  1. every locale defines exactly the same keys (parity),
 *  2. every `t('…')` key used in the app exists in the base locale,
 *  3. no non-English value is identical to English (i.e. actually translated),
 *     apart from a small allowlist of borrowed / proper-noun terms.
 */

const LOCALES = ["en", "es", "sw", "lg", "pt", "ar", "hi", "uk", "fr"] as const;
const BASE = "en";
const MSG_DIR = path.resolve("messages");

const load = (l: string): Record<string, string> =>
  JSON.parse(fs.readFileSync(path.join(MSG_DIR, `${l}.json`), "utf8"));
const data = Object.fromEntries(LOCALES.map((l) => [l, load(l)])) as Record<
  string,
  Record<string, string>
>;
const keysOf = (l: string) =>
  Object.keys(data[l]).filter((k) => k !== "$schema");

/**
 * Strings a locale has NOT translated yet — declared, rather than hidden.
 *
 * Different in kind from SAME_AS_ENGLISH_OK above, which is "identical to
 * English forever, and correctly so". This is debt, with a reason and a way out.
 *
 * Asserted EXACTLY, in both directions: a fifth untranslated string fails, and
 * so does fixing one of these four without deleting it from here. A pending
 * list that only ever grows is how "temporary" becomes permanent — same
 * two-way ratchet the English-audit baseline uses, for the same reason.
 */
// The book page's "more like this" reason labels. The keys ship to every
// catalogue for parity, but only en/es/pt/fr are translated and reviewed; the
// book page renders these only in those locales (its REVIEWED_LOCALES set), so
// the English placeholders below never reach a reader. Awaiting native review —
// when a locale's are translated, delete it here and add it to REVIEWED_LOCALES.
// (The old derived-FAQ keys were removed when books went editorial-only.)
const BOOK_EXTRAS_PENDING = ["book_more_by", "book_also_on"] as const;

// The sermon page's "Questions for reflection" heading. Same story as
// BOOK_EXTRAS_PENDING: en/es/pt/fr are translated and reviewed (the sermon
// page's REVIEWED_LOCALES), the rest hold the English source as a gated-off
// placeholder that never reaches a reader. Delete a locale's entry and add it to
// REVIEWED_LOCALES once a native speaker checks the heading.
const SERMON_EXTRAS_PENDING = ["sermon_questions_title"] as const;

// The book/topic Q&A section heading ("Questions and Answers"). Same story again:
// en/es/pt/fr are translated and reviewed, the rest hold the English source as a
// placeholder until a native speaker checks it. Delete a locale's entry once its
// heading is translated. (The Q&A section only renders where per-row Q&A content
// exists for the locale, so today the placeholder never reaches a reader anyway.)
const QA_EXTRAS_PENDING = ["qa_section_title"] as const;

// The reader-feedback button + modal strings. en/es/pt/fr are translated and
// reviewed; the placeholder locales below hold the English source until a native
// speaker checks them. Delete these once a locale's feedback strings are
// translated (they share one pending list across the placeholder locales).
const FEEDBACK_EXTRAS_PENDING = [
  "feedback_send",
  "feedback_title",
  "feedback_intro",
  "feedback_type",
  "feedback_type_language",
  "feedback_type_content",
  "feedback_type_feature",
  "feedback_type_bug",
  "feedback_type_other",
  "feedback_placeholder",
  "feedback_about",
  "feedback_submit",
  "feedback_sending",
  "feedback_thanks_title",
  "feedback_thanks_body",
  "feedback_error",
  "reader_suggest_edit",
  "feedback_edit_title",
  "feedback_edit_intro",
  "feedback_suggested_label",
  "feedback_suggested_placeholder",
] as const;

const UI_EXTRAS_PENDING = [
  ...BOOK_EXTRAS_PENDING,
  ...SERMON_EXTRAS_PENDING,
  ...QA_EXTRAS_PENDING,
  ...FEEDBACK_EXTRAS_PENDING,
];

const PENDING_TRANSLATION: Record<string, readonly string[]> = {
  // A blocked/awaiting-review string is declared here and ratcheted (asserted
  // exactly, both directions) rather than quietly allowlisted forever. uk's four
  // Scripture strings once lived here until the Kulish text could be sourced.
  sw: UI_EXTRAS_PENDING,
  lg: UI_EXTRAS_PENDING,
  hi: UI_EXTRAS_PENDING,
  ar: UI_EXTRAS_PENDING,
  uk: UI_EXTRAS_PENDING,
};

const toSnake = (key: string) =>
  key
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/\./g, "_")
    .toLowerCase();

function usedKeys(): Set<string> {
  const out = new Set<string>();
  const re = /\bt\(\s*['"`]([a-zA-Z0-9_.]+)['"`]\s*\)/g;
  const walk = (dir: string) => {
    for (const name of fs.readdirSync(dir)) {
      const p = path.join(dir, name);
      const stat = fs.statSync(p);
      if (stat.isDirectory()) {
        if (!p.includes("paraglide")) walk(p);
      } else if (/\.(svelte|ts)$/.test(name) && !name.endsWith(".test.ts")) {
        const src = fs.readFileSync(p, "utf8");
        for (let m; (m = re.exec(src));) out.add(toSnake(m[1]));
      }
    }
  };
  walk(path.resolve("src"));
  return out;
}

describe("i18n messages", () => {
  it("all locales define the same keys (parity)", () => {
    const base = new Set(keysOf(BASE));
    for (const l of LOCALES.filter((x) => x !== BASE)) {
      const here = new Set(keysOf(l));
      const missing = [...base].filter((k) => !here.has(k));
      const extra = [...here].filter((k) => !base.has(k));
      expect({ locale: l, missing, extra }).toEqual({
        locale: l,
        missing: [],
        extra: [],
      });
    }
  });

  it("every t() key used in the app exists in the base locale", () => {
    const base = new Set(keysOf(BASE));
    const missing = [...usedKeys()].filter((k) => !base.has(k)).sort();
    expect(missing).toEqual([]);
  });

  it("non-English strings are actually translated (or declared pending)", () => {
    // DERIVED from LOCALES, not a second hardcoded list. This check used to
    // carry its own copy of the locale array, which meant every new locale had
    // to be remembered in two places to be covered — and href.test.ts already
    // records what that costs: its locale list was literal, pt was wired in,
    // and the guard silently stopped covering /pt/. One list, one place.
    for (const l of LOCALES.filter((x) => x !== BASE)) {
      const untranslated = keysOf(BASE)
        .filter(
          (k) => !SAME_AS_ENGLISH_OK.has(k) && data[l][k] === data[BASE][k],
        )
        .sort();
      expect(
        { locale: l, untranslated },
        `${l} has untranslated strings that are not declared in PENDING_TRANSLATION. ` +
          "Translate them, or — if they are blocked on something (a Bible text, a " +
          "reviewer) — add them there with the reason. If a listed key is now " +
          "translated, delete it from PENDING_TRANSLATION.",
      ).toEqual({
        locale: l,
        untranslated: [...(PENDING_TRANSLATION[l] ?? [])].sort(),
      });
    }
  });
});
