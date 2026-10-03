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
export const WEEK = 7;

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
		const joins = cur && (d.article_slug || !d.book_slug || d.book_slug === cur.bookSlug || !cur.bookSlug);
		if (cur && joins) {
			// A run that opened on articles takes the first book it meets.
			if (!cur.bookSlug && d.book_slug && !d.article_slug) {
				cur.bookSlug = d.book_slug;
				cur.bookTitle = d.book_title;
			}
			cur.days.push(d);
			cur.last = d.day;
			continue;
		}
		const book = d.article_slug ? '' : d.book_slug;
		groups.push({
			key: `${book || 'articles'}-${d.day}`,
			bookSlug: book,
			bookTitle: book ? d.book_title : '',
			days: [d],
			first: d.day,
			last: d.day
		});
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
 * A chapter title without its own "Day 13 — " prefix. The row's circle already
 * shows the PLAN day, and the two disagree whenever a book opens on an
 * introduction (circle 14, "Day 13 — Where You Go, I'll Go"). Strips only the
 * plan language's word for "day" or the English one, followed by a number and
 * a separator — "Psalm 23 — The Shepherd" keeps its number.
 */
export function stripDayPrefix(title: string, dayWord: string): string {
	const words = [...new Set(['Day', dayWord].filter(Boolean))].map(escape).join('|');
	const re = new RegExp(`^(?:${words})\\s+\\d+\\s*[—–:.-]\\s*(?=\\S)`, 'iu');
	return title.replace(re, '');
}

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
