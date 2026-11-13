/**
 * "What the Church has said": a Bible chapter's catena, verse by verse.
 *
 * The chapter payload's `catena` names the spans its catena comments on; the
 * excerpts come from `getChapterCatena` when a reader opens one (CatenaPanel).
 * Pure, so the panel's two decisions are tested without a page.
 */

import type { CatenaPassage } from '$lib/library-public';
import { bookChapterPath } from '$lib/reading-schema';

/** The catena's chapter, opened at the block that quotes the span — the
 *  reader's `?p=` deep link (a block at the very top needs none). */
export const catenaPassageHref = (slug: string, chapter: number, p: number): string =>
	`${bookChapterPath(slug, chapter, false)}${p > 0 ? `?p=${p}` : ''}`;

/** The passage for a chip, or null when the served index has no such span
 *  (a prerendered chip racing a newer API). */
export const passageFor = (passages: readonly CatenaPassage[], ref: string): CatenaPassage | null =>
	passages.find((p) => p.ref === ref) ?? null;

/** A DOM-id-safe form of a span ("3:14–16" → "3-14-16"). */
export const spanId = (ref: string): string => ref.replace(/[^0-9a-z]+/gi, '-');
