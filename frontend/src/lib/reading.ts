/** Estimated reading time in whole minutes from a word count (~200 wpm). */
export function readingMinutes(words: number): number {
	return Math.max(1, Math.round(words / 200));
}

/** Human label, e.g. "12 min read" or "1 hr 5 min read". */
export function readingTime(words: number): string {
	const mins = readingMinutes(words);
	if (mins < 60) return `${mins} min read`;
	const h = Math.floor(mins / 60);
	const m = mins % 60;
	return m ? `${h} hr ${m} min read` : `${h} hr read`;
}
