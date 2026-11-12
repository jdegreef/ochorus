/**
 * The reader's place on a journey map (`journeyMaps.ts`), from the reading
 * position this device already keeps (`$lib/progress`, read by the book page),
 * and the road drawn through the stops. Pure, so both are tested beside it.
 */

export type StopState = 'passed' | 'here' | 'ahead';

export interface ReaderPlace {
	/** The chapter the reader is in (the book page's `resumeHere`), or null. */
	current: number | null;
	/** The furthest chapter reached, or null. */
	furthest: number | null;
	/** The book is stamped finished. */
	finished: boolean;
}

/**
 * Each stop's state. A finished book has passed every stop. Otherwise the
 * reader is at the FIRST stop of the chapter they are in (several places can
 * share a chapter — the Cross, Hill Difficulty and the House Beautiful are all
 * chapter 4, and a reader opening it is at the Cross), or, in a chapter with
 * no stop of its own, just past the last stop before it. Stops before that are
 * passed, the rest ahead. No place yet (or still before the first stop's
 * chapter, as in a book's preface) = everything ahead.
 */
export function journeyStates(stops: { chapter: number }[], place: ReaderPlace): StopState[] {
	if (place.finished) return stops.map(() => 'passed');
	const at = place.current ?? place.furthest;
	if (at == null) return stops.map(() => 'ahead');
	let here = stops.findIndex((s) => s.chapter === at);
	if (here < 0) here = stops.findLastIndex((s) => s.chapter < at);
	return stops.map((_, i) => (here < 0 || i > here ? 'ahead' : i === here ? 'here' : 'passed'));
}

const r = (n: number) => Math.round(n * 10) / 10;

/**
 * A smooth road through the points (a Catmull–Rom spline as cubic Béziers),
 * so the path bends through every stop rather than zig-zagging between them.
 */
export function roadPath(points: { x: number; y: number }[]): string {
	if (!points.length) return '';
	let d = `M${r(points[0].x)},${r(points[0].y)}`;
	for (let i = 0; i < points.length - 1; i++) {
		const p0 = points[i - 1] ?? points[i];
		const p1 = points[i];
		const p2 = points[i + 1];
		const p3 = points[i + 2] ?? p2;
		const c1 = { x: p1.x + (p2.x - p0.x) / 6, y: p1.y + (p2.y - p0.y) / 6 };
		const c2 = { x: p2.x - (p3.x - p1.x) / 6, y: p2.y - (p3.y - p1.y) / 6 };
		d += ` C${r(c1.x)},${r(c1.y)} ${r(c2.x)},${r(c2.y)} ${r(p2.x)},${r(p2.y)}`;
	}
	return d;
}
