/**
 * The plan page's day list, given a shape: the days grouped by the book they
 * read, and each long group cut into weeks — so a 96-day plan reads as three
 * books of five weeks, not one flat column of 96 rows.
 *
 * Pure, so the grouping is unit-tested apart from the page.
 */
import type { PlanDay } from './library-public';

/** A run of consecutive days reading the same book. */
export interface PlanGroup {
	/** Stable across renders: the book and the day the run starts on. */
	key: string;
	/** Empty for a run that opens on article days, before any book. */
	bookSlug: string;
	bookTitle: string;
	days: PlanDay[];
	first: number;
	last: number;
}

/** A group's days, in sevens. */
const WEEK = 7;

/**
 * Consecutive runs by book. An article day reads between a book's chapters,
 * so it stays in the run it sits in; only articles before any book open a run
 * of their own. A book read again later opens a second run — the list follows
 * the plan's order, which is the order the reader meets them.
 */
export function groupPlanDays(days: PlanDay[]): PlanGroup[] {
	const groups: PlanGroup[] = [];
	for (const d of days) {
		const cur = groups.at(-1);
		const reading = d.article_slug ? '' : d.book_slug;
		if (!cur || (reading && cur.bookSlug && reading !== cur.bookSlug)) {
			groups.push({
				key: `${reading || 'articles'}-${d.day}`,
				bookSlug: reading,
				bookTitle: reading ? d.book_title : '',
				days: [d],
				first: d.day,
				last: d.day
			});
			continue;
		}
		// A run that opened on articles takes the first book it meets.
		if (!cur.bookSlug && reading) {
			cur.bookSlug = reading;
			cur.bookTitle = d.book_title;
		}
		cur.days.push(d);
		cur.last = d.day;
	}
	return groups;
}

/** A group's days cut into weeks of seven; a group of a week or less is one. */
export function weeksOf(days: PlanDay[]): PlanDay[][] {
	const weeks: PlanDay[][] = [];
	for (let i = 0; i < days.length; i += WEEK) weeks.push(days.slice(i, i + WEEK));
	return weeks;
}

/**
 * Short labels for a plan's books, for the jump chips: what tells each title
 * apart once the words they all share are dropped. Three volumes of one
 * series ("Daughters of the King – … – Book 1/2/3") become "Book 1/2/3";
 * titles with nothing in common keep their whole text. The shared prefix is
 * cut back to a word boundary, so "Book 1" never loses its "Book".
 */
export function shortTitles(titles: string[]): string[] {
	if (titles.length < 2) return titles;
	const words = titles.map((t) => t.split(' '));
	let shared = 0;
	while (words.every((w) => shared < w.length - 1 && w[shared] === words[0][shared])) shared++;
	// A bare number ("1") says nothing alone: keep the word it numbers ("Book 1").
	if (shared && words.every((w) => /^(\d+|[IVXLC]+)$/.test(w.slice(shared).join(' ')))) shared--;
	return words.map((w) => w.slice(shared).join(' ').replace(/^[–—:-]\s*/u, ''));
}
