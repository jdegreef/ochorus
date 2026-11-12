/**
 * Typographer's quotation marks in reading text: `"But," said he` is set as
 * “But,” said he, and `the critic's observation` as the critic’s observation.
 *
 * At render time, not in the stored body, on purpose — and ONLY swaps that
 * keep the text the same length. A highlight is stored as character offsets
 * into a block's text plus `q`, the words it covered (`markAnchor.ts`), and a
 * bookmark by its paragraph's opening words; one straight mark for one curly
 * mark moves no offset, and the anchor comparisons fold curly quotes back to
 * straight on both sides (`foldQuotes` here, `_fold` in backend
 * reading/anchor.py), so marks made before this — or on a body that already
 * had curly quotes — still find their words. `--` → `—` and `...` → `…` change
 * the length, so they are deliberately NOT done here (and the stored bodies
 * hold no `--` anyway: `library/dashes.py` repairs those at deploy).
 *
 * Per language, and only where the convention is clear:
 * - FULL (“ ” ‘ ’): English, Spanish and Portuguese (whose bodies already use
 *   “ ” as their secondary/curly marks alongside « »), Swahili, Luganda,
 *   Hindi, Korean, Vietnamese.
 * - APOSTROPHE only (l'homme → l’homme, п'ять → п’ять): French and
 *   Ukrainian, whose double quotes are « » (French with narrow no-break spaces
 *   — inserting those would change the length) or „ “; their bodies already
 *   carry those, so straight doubles are left as they are.
 * - Anything else (Arabic, Amharic, a language added later): unchanged. A
 *   wrong guess at a language's marks is worse than a straight one.
 *
 * Never inside `<code>`/`<pre>`/`<kbd>`/`<samp>`/`<script>`/`<style>`, never
 * in a tag's attributes, and never inside a URL written out in the text.
 */

type Style = "full" | "apostrophe";

const STYLES: Record<string, Style> = {
  en: "full",
  es: "full",
  pt: "full",
  sw: "full",
  lg: "full",
  hi: "full",
  ko: "full",
  vi: "full",
  fr: "apostrophe",
  uk: "apostrophe",
};

const L_DOUBLE = "“";
const R_DOUBLE = "”";
const L_SINGLE = "‘";
const R_SINGLE = "’";

/** How a content language's quotes are set, or null to leave them alone.
 *  Keyed by the base subtag, so the `en-modern` edition is English. */
export function quoteStyle(language: string | null | undefined): Style | null {
  return STYLES[(language ?? "").toLowerCase().split(/[-_]/)[0]] ?? null;
}

/** Curly quotes folded back to straight — one character for one, so an index
 *  into the folded string is an index into the original. What anchors compare. */
export function foldQuotes(s: string): string {
  return s.replace(/[‘’]/g, "'").replace(/[“”]/g, '"');
}

const isSpace = (c: string): boolean => c === "" || /\s/.test(c);
const isWord = (c: string): boolean => c !== "" && /[\p{L}\p{M}\p{N}]/u.test(c);
const isDash = (c: string): boolean =>
  c === "—" || c === "–" || c === "-" || c === "‐";
/** After one of these a quote opens: brackets, dashes, slashes and other
 *  opening quotation marks (nested quotes). */
const OPENERS = new Set([
  "(",
  "[",
  "{",
  "<",
  "/",
  "«",
  "„",
  "‚",
  "‹",
  L_DOUBLE,
  L_SINGLE,
  "¿",
  "¡",
]);
/** Punctuation that follows a closing quote, never an opening one. */
const CLOSERS = new Set([".", ",", ";", ":", "!", "?", ")", "]"]);
const opensAfter = (c: string): boolean =>
  isSpace(c) || isDash(c) || OPENERS.has(c);

/** English words that begin with an elided letter — `'tis`, `'twas`, `'em` —
 *  whose leading mark is an apostrophe, not an opening quote. */
const ELISIONS = new Set([
  "tis",
  "twas",
  "twere",
  "twill",
  "twould",
  "twixt",
  "tween",
  "em",
  "neath",
  "gainst",
  "mid",
  "midst",
  "bout",
  "cause",
]);

/**
 * The replacement for the quote character at `text[i]`, or null to leave it.
 * `text` is the whole run of prose the quote sits in (so a quote's neighbours
 * across inline tags are visible); block boundaries are '\n'.
 */
function curl(
  text: string,
  i: number,
  style: Style,
  english: boolean,
): string | null {
  const ch = text[i];
  const prev = i > 0 ? text[i - 1] : "";
  const next = i + 1 < text.length ? text[i + 1] : "";
  if (style === "apostrophe") {
    // Only the unambiguous case: inside a word.
    return ch === "'" && isWord(prev) && isWord(next) ? R_SINGLE : null;
  }
  if (ch === '"') {
    if (!opensAfter(prev)) return R_DOUBLE; // after a word or closing punctuation
    // `old paths "?` — a stray space before a closing quote and its punctuation.
    if (CLOSERS.has(next) && isSpace(text[i + 2] ?? "")) return R_DOUBLE;
    if (!isSpace(next)) return L_DOUBLE;
    // "I thought—" then silence: a dash before a quote with nothing after it.
    if (isDash(prev)) return R_DOUBLE;
    return null; // stranded between spaces: no way to tell
  }
  // A single mark after a word is an apostrophe (critic’s, don’t, saints’)
  // or a closing quote — the same glyph.
  if (!opensAfter(prev)) return R_SINGLE;
  if (isSpace(next)) return isDash(prev) ? R_SINGLE : null;
  // A year ('45) or an elided word ('tis) opens on an apostrophe.
  if (/\p{N}/u.test(next)) return R_SINGLE;
  if (english) {
    const word = /^[\p{L}]+/u.exec(text.slice(i + 1))?.[0].toLowerCase();
    if (word && ELISIONS.has(word)) return R_SINGLE;
  }
  return L_SINGLE;
}

const URL_RE = /\b(?:https?:\/\/|www\.)\S+/gi;

/** Indices of `text` that sit inside a URL. */
function urlSpans(text: string): Set<number> {
  const out = new Set<number>();
  for (const m of text.matchAll(URL_RE))
    for (let k = 0; k < m[0].length; k++) out.add(m.index + k);
  return out;
}

/** `text` with its quotes curled, one UTF-16 unit for one (every mark here
 *  is in the BMP), so an index into the result is an index into `text`. */
function curlAll(
  text: string,
  style: Style,
  english: boolean,
  frozen: (i: number) => boolean,
): string {
  const urls = urlSpans(text);
  const out = text.split("");
  for (let i = 0; i < out.length; i++) {
    if ((out[i] === '"' || out[i] === "'") && !frozen(i) && !urls.has(i)) {
      out[i] = curl(text, i, style, english) ?? out[i];
    }
  }
  return out.join("");
}

const isEnglish = (language: string | null | undefined): boolean =>
  (language ?? "").toLowerCase().split(/[-_]/)[0] === "en";

/** Plain text (an author's one-line lede, a tagline) with curly quotes. */
export function smartQuotes(
  text: string,
  language: string | null | undefined,
): string {
  const style = quoteStyle(language);
  if (!style || !text || !/["']/.test(text)) return text;
  return curlAll(text, style, isEnglish(language), () => false);
}

/** Elements whose text is never typography. */
const VERBATIM = new Set([
  "code",
  "pre",
  "kbd",
  "samp",
  "script",
  "style",
  "tt",
  "var",
]);
/** Elements that end one run of prose and start another: a quote at the start
 *  of a paragraph opens, whatever ended the paragraph before it. */
const BLOCK = new Set([
  "p",
  "div",
  "br",
  "hr",
  "li",
  "ul",
  "ol",
  "dl",
  "dt",
  "dd",
  "blockquote",
  "section",
  "article",
  "aside",
  "header",
  "footer",
  "figure",
  "figcaption",
  "table",
  "tr",
  "td",
  "th",
  "caption",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "img",
]);
/** The entities a sanitiser writes for a quote, and the few others whose
 *  character matters as a quote's neighbour. Anything else reads as a letter. */
const ENTITY: Record<string, string> = {
  quot: '"',
  "#34": '"',
  "#x22": '"',
  apos: "'",
  "#39": "'",
  "#x27": "'",
  nbsp: " ",
  "#160": " ",
  "#xa0": " ",
  amp: "&",
  lt: "<",
  gt: ">",
  mdash: "—",
  ndash: "–",
  lsquo: L_SINGLE,
  rsquo: R_SINGLE,
  ldquo: L_DOUBLE,
  rdquo: R_DOUBLE,
};

const TOKEN =
  /<!--[\s\S]*?-->|<\/?([a-zA-Z][\w-]*)[^>]*>|&(#x?[\da-fA-F]+|\w+);|[^<&]+|[<&]/g;

/**
 * An HTML fragment (a chapter, sermon or biography body) with curly quotes in
 * its text. Text is read across inline tags, so `"<em>But</em>,"` opens and
 * closes correctly; tags, attributes and comments pass through untouched. A
 * quote written as an entity (`&quot;`, `&#x27;`) becomes the curly character
 * itself — one character of `textContent` for one.
 */
export function smartQuotesHtml(
  html: string,
  language: string | null | undefined,
): string {
  const style = quoteStyle(language);
  if (!style || !html || !/["']|&(quot|apos|#34|#39|#x2[27]);/i.test(html))
    return html;

  // Pass 1: the text as the reader sees it — an entity as its one character, a
  // '\n' at each block boundary — and where each piece of it came from. A
  // piece is a tag or comment (passed through), an entity, or a run of text.
  type Piece = { raw: string; at: number; kind: "markup" | "entity" | "text" };
  const pieces: Piece[] = [];
  const frozen = new Set<number>();
  let text = "";
  let verbatim = 0;
  for (const m of html.matchAll(TOKEN)) {
    const raw = m[0];
    const at = text.length;
    if (m[1] !== undefined) {
      const name = m[1].toLowerCase();
      if (VERBATIM.has(name) && !raw.endsWith("/>"))
        verbatim = Math.max(0, verbatim + (raw[1] === "/" ? -1 : 1));
      if (BLOCK.has(name)) text += "\n";
      pieces.push({ raw, at, kind: "markup" });
      continue;
    }
    if (raw.startsWith("<!--")) {
      pieces.push({ raw, at, kind: "markup" });
      continue;
    }
    const entity = m[2] !== undefined;
    text += entity ? (ENTITY[m[2].toLowerCase()] ?? "x") : raw;
    if (verbatim) for (let k = at; k < text.length; k++) frozen.add(k);
    pieces.push({ raw, at, kind: entity ? "entity" : "text" });
  }

  // Pass 2: decide each quote from its neighbours in that text, then write the
  // pieces back. `curled` differs from `text` only at the quotes it turned.
  const curled = curlAll(text, style, isEnglish(language), (i) =>
    frozen.has(i),
  );
  let out = "";
  for (const p of pieces) {
    if (p.kind === "text") out += curled.slice(p.at, p.at + p.raw.length);
    else if (p.kind === "entity" && curled[p.at] !== text[p.at])
      out += curled[p.at];
    else out += p.raw;
  }
  return out;
}
