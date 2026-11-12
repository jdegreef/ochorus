/**
 * A book published in parts (`Book.parts`): The Pilgrim's Progress, Part One
 * (1678) and Part Two (1684). A part runs from its `first_chapter` to the next
 * part's; chapters before the first part (none today) belong to no part.
 *
 * Pure helpers, shared by the book page's contents, the reader's contents
 * drawer and the chapter page's <title>.
 */
import type { BookPart, ChapterPart } from '$lib/library-public';

/** The part chapter `order` is in, or null (no parts, or before the first). */
export function partOf<P extends BookPart>(parts: P[] | undefined, order: number): P | null {
	let found: P | null = null;
	for (const p of parts ?? []) if (p.first_chapter <= order) found = p;
	return found;
}

export interface PartGroup<C> {
	part: BookPart | null;
	chapters: C[];
}

/**
 * The chapters in runs by part, in order — one group with `part: null` for a
 * book in one piece. A part no chapter of this edition falls in is dropped:
 * a heading over nothing says nothing.
 */
export function partGroups<C extends { order: number }>(
	chapters: C[],
	parts: BookPart[] | undefined
): PartGroup<C>[] {
	const groups: PartGroup<C>[] = [];
	for (const ch of chapters) {
		const part = partOf(parts, ch.order);
		const last = groups.at(-1);
		if (last && last.part === part) last.chapters.push(ch);
		else groups.push({ part, chapters: [ch] });
	}
	return groups;
}

/**
 * The orders a collapsed contents list keeps in view so each part reads as a
 * part: its first and last chapter. Empty for a book in one piece.
 */
export function partEnds(groups: PartGroup<{ order: number }>[]): number[] {
	return groups.filter((g) => g.part).flatMap((g) => [g.chapters[0].order, g.chapters.at(-1)!.order]);
}

/** "Part One · 1678" — the heading's eyebrow. */
export function partLine(part: ChapterPart): string {
	return part.year ? `${part.title} · ${part.year}` : part.title;
}

/**
 * A chapter's name where it must stand alone (the <title>, a search snippet):
 * "The First Stage (Part Two)" when another chapter shares the title and a
 * part tells them apart, else the name as given.
 */
export function partQualified(name: string, part: ChapterPart | null | undefined, repeats: boolean | undefined): string {
	return repeats && part ? `${name} (${part.title})` : name;
}
