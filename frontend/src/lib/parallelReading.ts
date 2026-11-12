import { MODERN_EDITION } from './reading-schema';

/**
 * "Side by side": the Original on the left, the Modern English edition on the
 * right, one row per paragraph. Pure decisions only — the component
 * (ParallelModern.svelte) and the chapter reader do the DOM.
 *
 * Why paragraph index is a sound key: the Modern English edition is written
 * one chapter at a time to the SAME top-level block count as the original
 * (contemporize-book skill — marks and the reading position already carry
 * across the edition toggle by that index), and the light pass is a word map
 * that never touches the markup. Measured on the fixture, 2026-11-12: all 132
 * modern chapters across 6 works match their original block for block, tags
 * included. But nothing ENFORCES it, so the reader checks per chapter and
 * never pairs blocks it can't vouch for.
 */

/** How the two columns relate: paired row by row, or two texts that each
 *  scroll on their own (the honest fallback when the block counts differ). */
export type ParallelLayout = 'rows' | 'columns';

/**
 * Rows only when both editions split the chapter into the same number of
 * top-level blocks (the unit `?p=`, marks and bookmarks index). A mismatch —
 * a merged or split paragraph in a careful pass — would pair every block after
 * it with the wrong one, so it falls back to free columns instead of
 * misaligning silently. An empty text has nothing to pair.
 */
export function parallelLayout(originalBlocks: number, modernBlocks: number): ParallelLayout {
	return originalBlocks > 0 && originalBlocks === modernBlocks ? 'rows' : 'columns';
}

/** A chapter's top-level blocks — the same split `markText.paragraphs` and the
 *  reader's `body.children` use. A <template>, so nothing in it loads. */
export function blockCount(html: string): number {
	const tpl = document.createElement('template');
	tpl.innerHTML = html;
	return tpl.content.children.length;
}

/** Per row, the height both cells take: the taller of the pair. */
export function rowHeights(original: readonly number[], modern: readonly number[]): number[] {
	return original.map((h, i) => Math.max(h, modern[i] ?? 0));
}

export interface ParallelGate {
	/** The work has a Modern English edition (`chapter.has_modern_edition`). */
	hasModern: boolean | undefined;
	/** The edition actually shown (`data.language`): 'en', 'en-modern', or a
	 *  translation — which has no Modern English twin to sit beside. */
	language: string;
	/** Wide enough for two comfortable columns (desktop / landscape tablet). */
	wide: boolean;
}

/** Whether the reader offers the mode at all: an English work with a Modern
 *  English edition, on a screen wide enough for two columns. Never on phones. */
export function parallelOffered(g: ParallelGate): boolean {
	return !!g.hasModern && g.wide && (g.language === 'en' || g.language === MODERN_EDITION);
}

/**
 * Whether the open page lays out side by side. Only on the ORIGINAL edition's
 * route: its body is the left column, so highlights, bookmarks, Listen and the
 * reading position keep working on the very element they always did. On the
 * Modern route the menu item leads back to the Original with the mode on.
 */
export function parallelActive(g: ParallelGate & { pref: boolean; edition: 'modern' | null }): boolean {
	return g.pref && g.edition !== 'modern' && g.language === 'en' && parallelOffered(g);
}
