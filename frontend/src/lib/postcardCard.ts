// The quote card's second style: a vintage postcard. Same job as `quoteCard.ts`
// — a reader's selected line, turned into a PNG built to leave the site (and,
// for much of the non-English audience, to travel by WhatsApp) — dressed as a
// card sent through the post: aged stock, the quote on the message half, a
// divider, an address half with ruled lines, a stamp in the book's own cover
// colour, and a postmark naming where and when the work was written.
//
// hex-ok-file: like the quote card, this paints a fixed palette into a PNG that
// leaves the site. It has no theme to follow; the stamp's colour is the book's
// `cover_color`, which is data (STYLE_GUIDE §1), not a UI colour.
//
// THE POSTMARK STATES ONLY WHAT THE DATA SAYS. It carries the work's city and
// year when the caller has them, each independently; with neither, the round
// mark is left off altogether (the cancellation waves over the stamp are pure
// ornament and stay). The library records a book's `publication_year` but no
// place of writing and no author city, so today a postmark is a year or
// nothing — never a guessed "London".
//
// Split into a pure LAYOUT (`layoutPostcard`, measured through any object with
// `font` and `measureText`, so tests run it without a canvas) and a painter
// that draws exactly what the layout says. Every position is computed for a
// left-to-right card and mirrored whole for a right-to-left one, so an Arabic
// postcard reads from the right: the message on the right half, the stamp and
// the address on the left.

import { channels, inkSafe } from "$lib/coverArt";
import {
  type CardShareResult,
  cardScript,
  drawMark,
  ensureFonts,
  fitQuote,
  quoteStyle,
  shareCardImage,
  SIZE,
  trimQuote,
  wrapLines,
} from "$lib/quoteCard";

export interface PostcardOptions {
  quote: string;
  author: string;
  /** Where it's from, e.g. "Humility, Chapter 1". */
  source: string;
  /** Footer site label, e.g. "ochorus.com". */
  site?: string;
  /** The edition's language — sets the script, the digits and the direction. */
  language?: string;
  /** The book's `cover_color`; the stamp falls back to a postal red without it. */
  color?: string | null;
  /** Where the work was written — only ever from data; omitted when unknown. */
  city?: string | null;
  /** The work's year (`publication_year`) — omitted when unknown. */
  year?: number | null;
}

/**
 * The classic face the message is set in: EB Garamond (the "classic" site
 * style, upright and italic both declared in app.css), then the same per-script
 * faces as the quote card's stack, so an Arabic or Devanagari line falls to
 * Amiri or Tiro rather than to the device.
 */
export const POSTCARD_SERIF =
  "'EB Garamond Variable', 'Amiri', 'Tiro Devanagari Hindi', 'Noto Serif Ethiopic', 'Noto Serif JP', 'Noto Serif KR', 'PT Serif', Georgia, 'Times New Roman', serif";

/** Aged card stock: the ground, its darker edges, and the ink written on it. */
const STOCK = "#efe3c7";
const STOCK_EDGE = "#d8c39a";
const INK = "#2a2118";
const MUTED = "#6d5f4c";
const RULE = "rgba(42,33,24,0.32)";
/** Postmark ink — the faded violet-grey of a hand stamp. */
const POSTMARK = "rgba(64,46,78,0.62)";
/** A stamp for a work with no cover colour (a sermon, an older API). */
const POSTAL_RED = "#8c2f2f";

/** Just what the layout needs from a canvas context. */
export type TextMeasure = Pick<
  CanvasRenderingContext2D,
  "font" | "measureText"
>;

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface PostcardLayout {
  rtl: boolean;
  /** The message half: the quote, fitted, and where its lines start. */
  quote: {
    lines: string[];
    font: string;
    lineHeight: number;
    box: Box;
    top: number;
  };
  /** Author and source under the quote; `x` is the text's start edge. */
  attribution: {
    x: number;
    author: string;
    authorY: number;
    source: string[];
    sourceY: number;
  };
  /** A short gold-less rule between quote and attribution. */
  flourish: { x1: number; x2: number; y: number };
  divider: { x: number; y1: number; y2: number };
  stamp: Box & { ground: string };
  /** The round mark; null when there is nothing true to print in it. */
  postmark: { cx: number; cy: number; r: number; lines: string[] } | null;
  /** Wavy cancellation lines over the stamp. */
  cancel: { x1: number; x2: number; ys: number[] };
  rules: { x1: number; x2: number; ys: number[] };
  footer: Box;
}

// The left-to-right geometry, on the 1080 square every card is drawn at.
const EDGE = 40; // the frame inset
const MID = SIZE / 2;
const MSG: Box = { x: 84, y: 132, w: MID - 84 - 44, h: 640 };
const ADDR_X1 = MID + 44;
const ADDR_X2 = SIZE - 76;
const STAMP: Box = { x: ADDR_X2 - 156, y: 92, w: 156, h: 188 };
const POSTMARK_R = 84;

/** The postmark's lines, or null when there is no data for one. */
export function postmarkLines(
  city: string | null | undefined,
  year: number | null | undefined,
  language = "en",
): string[] | null {
  const lines: string[] = [];
  const place = city?.trim();
  if (place) lines.push(place.toLocaleUpperCase(language));
  if (typeof year === "number" && Number.isInteger(year) && year > 0) {
    // Plain digits, as the site prints every year — `Intl` would make the
    // Arabic card's digits depend on the device's CLDR.
    lines.push(`· ${year} ·`);
  }
  return lines.length ? lines : null;
}

/** The stamp's ground: the cover colour, darkened until white type on it reads. */
export function stampGround(color: string | null | undefined): string {
  return inkSafe(color && /^#[0-9a-f]{6}$/i.test(color) ? color : POSTAL_RED);
}

/** Wrap to at most `max` lines, closing a cut with an ellipsis. */
function clampLines(
  ctx: TextMeasure,
  text: string,
  width: number,
  max: number,
): string[] {
  const lines = wrapLines(ctx as CanvasRenderingContext2D, text, width);
  if (lines.length <= max) return lines;
  const kept = lines.slice(0, max);
  kept[max - 1] = `${kept[max - 1].replace(/[,;:.\s]+$/, "")}…`;
  return kept;
}

/** Mirror a box across the card's vertical centre line. */
const flip = (b: Box): Box => ({ ...b, x: SIZE - b.x - b.w });

/** Where everything goes. Pure: measures through `ctx` and draws nothing. */
export function layoutPostcard(
  ctx: TextMeasure,
  opts: PostcardOptions,
): PostcardLayout {
  const language = opts.language ?? "en";
  const script = cardScript(language);
  const rtl = script === "arabic";
  const style = quoteStyle(script);

  const quote = trimQuote(opts.quote);
  const fit = fitQuote(
    ctx as CanvasRenderingContext2D,
    quote,
    MSG.w,
    MSG.h,
    style,
    58,
    26,
    POSTCARD_SERIF,
  );
  const blockHeight = fit.lines.length * fit.lineHeight;
  const top = MSG.y + Math.max(0, (MSG.h - blockHeight) / 2);

  ctx.font = `400 23px ${POSTCARD_SERIF}`;
  const source = opts.source ? clampLines(ctx, opts.source, MSG.w, 2) : [];
  ctx.font = `600 29px ${POSTCARD_SERIF}`;
  const [author] = clampLines(ctx, opts.author, MSG.w, 1);

  const lines = postmarkLines(opts.city, opts.year, language);
  const ltr: PostcardLayout = {
    rtl,
    quote: {
      lines: fit.lines,
      font: `${style} ${fit.fontSize}px ${POSTCARD_SERIF}`,
      lineHeight: fit.lineHeight,
      box: MSG,
      top,
    },
    attribution: {
      x: MSG.x,
      author: author ?? "",
      authorY: 838,
      source,
      sourceY: 880,
    },
    flourish: { x1: MSG.x, x2: MSG.x + 64, y: 810 },
    divider: { x: MID, y1: 112, y2: SIZE - 112 },
    stamp: { ...STAMP, ground: stampGround(opts.color) },
    postmark: lines
      ? {
          cx: STAMP.x - 34,
          cy: STAMP.y + STAMP.h / 2 + 18,
          r: POSTMARK_R,
          lines,
        }
      : null,
    cancel: {
      x1: STAMP.x - 22,
      x2: SIZE - EDGE - 6,
      ys: [146, 172, 198, 224].map((y) => y + 12),
    },
    rules: { x1: ADDR_X1, x2: ADDR_X2, ys: [548, 640, 732, 824] },
    footer: { x: ADDR_X1, y: 900, w: ADDR_X2 - ADDR_X1, h: 40 },
  };
  if (!rtl) return ltr;

  // Mirrored whole: every x measured from the other edge. The quote and
  // attribution keep their start edge, which is now the RIGHT one.
  const fx = (x: number) => SIZE - x;
  return {
    ...ltr,
    quote: { ...ltr.quote, box: flip(ltr.quote.box) },
    attribution: { ...ltr.attribution, x: fx(ltr.attribution.x) },
    flourish: {
      ...ltr.flourish,
      x1: fx(ltr.flourish.x1),
      x2: fx(ltr.flourish.x2),
    },
    divider: { ...ltr.divider, x: fx(ltr.divider.x) },
    stamp: { ...flip(ltr.stamp), ground: ltr.stamp.ground },
    postmark: ltr.postmark && { ...ltr.postmark, cx: fx(ltr.postmark.cx) },
    cancel: { ...ltr.cancel, x1: fx(ltr.cancel.x2), x2: fx(ltr.cancel.x1) },
    rules: { ...ltr.rules, x1: fx(ltr.rules.x2), x2: fx(ltr.rules.x1) },
    footer: flip(ltr.footer),
  };
}

/** A small deterministic generator, so the foxing is the same on every card. */
function seeded(seed: number) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function drawStock(ctx: CanvasRenderingContext2D) {
  const g = ctx.createRadialGradient(
    MID,
    MID,
    SIZE * 0.2,
    MID,
    MID,
    SIZE * 0.75,
  );
  g.addColorStop(0, STOCK);
  g.addColorStop(1, STOCK_EDGE);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, SIZE, SIZE);
  // Foxing: a few faint brown spots, as old card collects.
  const rnd = seeded(1886);
  for (let i = 0; i < 26; i++) {
    const x = rnd() * SIZE;
    const y = rnd() * SIZE;
    const r = 3 + rnd() * 16;
    const spot = ctx.createRadialGradient(x, y, 0, x, y, r);
    spot.addColorStop(0, `rgba(140,98,48,${0.05 + rnd() * 0.07})`);
    spot.addColorStop(1, "rgba(140,98,48,0)");
    ctx.fillStyle = spot;
    ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }
  ctx.strokeStyle = "rgba(42,33,24,0.22)";
  ctx.lineWidth = 2;
  ctx.strokeRect(
    EDGE + 0.5,
    EDGE + 0.5,
    SIZE - EDGE * 2 - 1,
    SIZE - EDGE * 2 - 1,
  );
}

function drawStamp(ctx: CanvasRenderingContext2D, s: PostcardLayout["stamp"]) {
  const hole = 6;
  const step = 16;
  ctx.save();
  // Perforations: clip to the stamp, then out of it a row of half-holes along
  // each edge (two clips intersect — an even-odd ring alone would keep the
  // halves outside the edge instead).
  ctx.beginPath();
  ctx.rect(s.x, s.y, s.w, s.h);
  ctx.clip();
  ctx.beginPath();
  ctx.rect(0, 0, SIZE, SIZE);
  for (let x = s.x + step / 2; x < s.x + s.w; x += step) {
    for (const y of [s.y, s.y + s.h]) {
      ctx.moveTo(x + hole, y);
      ctx.arc(x, y, hole, 0, Math.PI * 2);
    }
  }
  for (let y = s.y + step / 2; y < s.y + s.h; y += step) {
    for (const x of [s.x, s.x + s.w]) {
      ctx.moveTo(x + hole, y);
      ctx.arc(x, y, hole, 0, Math.PI * 2);
    }
  }
  ctx.clip("evenodd");
  ctx.shadowColor = "rgba(42,33,24,0.25)";
  ctx.shadowBlur = 6;
  ctx.fillStyle = "#fbf6ea";
  ctx.fillRect(s.x, s.y, s.w, s.h);
  ctx.restore();

  const inset = 14;
  const inner = {
    x: s.x + inset,
    y: s.y + inset,
    w: s.w - inset * 2,
    h: s.h - inset * 2,
  };
  ctx.fillStyle = s.ground;
  ctx.fillRect(inner.x, inner.y, inner.w, inner.h);
  // A lighter engraved band along the foot, from the same hue.
  const [r, g, b] = channels(s.ground);
  ctx.fillStyle = `rgba(${Math.min(255, r + 60)},${Math.min(255, g + 60)},${Math.min(255, b + 60)},0.35)`;
  ctx.fillRect(inner.x, inner.y + inner.h - 40, inner.w, 40);
  ctx.strokeStyle = "rgba(255,255,255,0.7)";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(inner.x + 6.5, inner.y + 6.5, inner.w - 13, inner.h - 13);

  const mark = 64;
  drawMark(ctx, inner.x + (inner.w - mark) / 2, inner.y + 26, mark, "#ffffff");
  ctx.fillStyle = "#ffffff";
  ctx.font = "600 17px 'Fraunces Variable', Georgia, serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.direction = "ltr";
  ctx.letterSpacing = "3px";
  ctx.fillText("OCHORUS", inner.x + inner.w / 2 + 1.5, inner.y + inner.h - 14);
  ctx.letterSpacing = "0px";
}

function drawCancel(
  ctx: CanvasRenderingContext2D,
  c: PostcardLayout["cancel"],
) {
  ctx.strokeStyle = POSTMARK;
  ctx.lineWidth = 3;
  for (const y of c.ys) {
    ctx.beginPath();
    for (let x = c.x1; x <= c.x2; x += 4) {
      const wy = y + Math.sin((x - c.x1) / 14) * 5;
      if (x === c.x1) ctx.moveTo(x, wy);
      else ctx.lineTo(x, wy);
    }
    ctx.stroke();
  }
}

function drawPostmark(
  ctx: CanvasRenderingContext2D,
  p: NonNullable<PostcardLayout["postmark"]>,
) {
  ctx.save();
  ctx.translate(p.cx, p.cy);
  ctx.rotate(-0.16);
  ctx.strokeStyle = POSTMARK;
  ctx.fillStyle = POSTMARK;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(0, 0, p.r, 0, Math.PI * 2);
  ctx.stroke();
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(0, 0, p.r - 10, 0, Math.PI * 2);
  ctx.stroke();
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const room = (p.r - 18) * 2;
  const gap = 34;
  p.lines.forEach((line, i) => {
    const y = (i - (p.lines.length - 1) / 2) * gap;
    // Shrink a long city name until it sits inside the ring.
    for (let fs = 26; fs >= 12; fs -= 1) {
      ctx.font = `700 ${fs}px ${POSTCARD_SERIF}`;
      if (ctx.measureText(line).width <= room) break;
    }
    ctx.fillText(line, 0, y);
  });
  ctx.restore();
}

/** Paint a layout. Exported for the sample-rendering script. */
export function paintPostcard(
  ctx: CanvasRenderingContext2D,
  l: PostcardLayout,
  site?: string,
) {
  drawStock(ctx);

  const start: CanvasTextAlign = l.rtl ? "right" : "left";
  ctx.direction = l.rtl ? "rtl" : "ltr";

  // Message half.
  ctx.fillStyle = INK;
  ctx.font = l.quote.font;
  ctx.textAlign = start;
  ctx.textBaseline = "top";
  const qx = l.rtl ? l.quote.box.x + l.quote.box.w : l.quote.box.x;
  l.quote.lines.forEach((line, i) =>
    ctx.fillText(line, qx, l.quote.top + i * l.quote.lineHeight),
  );

  ctx.strokeStyle = RULE;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(l.flourish.x1, l.flourish.y);
  ctx.lineTo(l.flourish.x2, l.flourish.y);
  ctx.stroke();

  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = INK;
  ctx.font = `600 29px ${POSTCARD_SERIF}`;
  ctx.fillText(l.attribution.author, l.attribution.x, l.attribution.authorY);
  ctx.fillStyle = MUTED;
  ctx.font = `400 23px ${POSTCARD_SERIF}`;
  l.attribution.source.forEach((line, i) =>
    ctx.fillText(line, l.attribution.x, l.attribution.sourceY + i * 30),
  );

  // The divider, and the address half's ruled lines.
  ctx.strokeStyle = RULE;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(l.divider.x, l.divider.y1);
  ctx.lineTo(l.divider.x, l.divider.y2);
  ctx.stroke();
  ctx.lineWidth = 1.5;
  for (const y of l.rules.ys) {
    ctx.beginPath();
    ctx.moveTo(l.rules.x1, y);
    ctx.lineTo(l.rules.x2, y);
    ctx.stroke();
  }

  drawStamp(ctx, l.stamp);
  drawCancel(ctx, l.cancel);
  if (l.postmark) drawPostmark(ctx, l.postmark);

  // The imprint along the foot of the address half, as a postcard printer's:
  // the mark and wordmark at one end, the site at the other. Latin either way.
  const f = l.footer;
  ctx.direction = "ltr";
  drawMark(ctx, f.x, f.y, 30, MUTED);
  ctx.fillStyle = MUTED;
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";
  ctx.font = "700 22px 'Fraunces Variable', Georgia, serif";
  ctx.fillText("Ochorus", f.x + 40, f.y + 25);
  if (site) {
    ctx.textAlign = "right";
    ctx.font = "400 20px Georgia, serif";
    ctx.fillText(site, f.x + f.w, f.y + 25);
  }
  ctx.textAlign = "left";
}

/** Render the postcard to a PNG Blob — the same 1080 square as the quote card. */
export async function renderPostcard(opts: PostcardOptions): Promise<Blob> {
  const script = cardScript(opts.language ?? "en");
  const text = [opts.quote, opts.author, opts.source, opts.city ?? ""].join(
    " ",
  );
  const fonts = (document as Document & { fonts?: FontFaceSet }).fonts;
  await Promise.all([
    ensureFonts(script, text),
    // The postcard's own classic face; ensureFonts loads the quote card's.
    fonts
      ?.load(`${quoteStyle(script)} 48px 'EB Garamond Variable'`, text)
      .then(() => fonts.load(`600 29px 'EB Garamond Variable'`, text))
      .catch(() => undefined),
  ]);
  const canvas = document.createElement("canvas");
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("canvas 2d unavailable");
  paintPostcard(ctx, layoutPostcard(ctx, opts), opts.site);
  return await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("toBlob failed"))),
      "image/png",
    );
  });
}

/** Render the postcard and hand it off, exactly as the quote card is. */
export async function sharePostcard(
  opts: PostcardOptions,
): Promise<CardShareResult> {
  const blob = await renderPostcard(opts);
  return shareCardImage(
    blob,
    "ochorus-postcard.png",
    `"${trimQuote(opts.quote)}" — ${opts.author}`,
  );
}
