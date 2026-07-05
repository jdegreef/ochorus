import { listBooks, listAuthors, listPlans, getPlan } from '$lib/library';
import { getLang } from '$lib/lang.svelte';
import { planProgress } from '$lib/planProgress.svelte';
import type { PageLoad } from './$types';

/** "Reading of the day": the next unread day of a started plan, or a plan to start. */
async function readingOfTheDay(language: string) {
	try {
		const plans = await listPlans(language);
		if (!plans.length) return null;

		// Prefer the most recently started, unfinished plan; else feature the first.
		const started = planProgress
			.started()
			.map(({ slug }) => plans.find((p) => p.slug === slug))
			.filter((p): p is NonNullable<typeof p> => !!p)
			.filter((p) => planProgress.nextDay(p.slug, p.day_count) !== null);
		const pick = started[0] ?? plans[0];
		const isStarted = planProgress.isStarted(pick.slug);
		const day = planProgress.nextDay(pick.slug, pick.day_count) ?? 1;

		const detail = await getPlan(pick.slug, language);
		const entry = detail.days.find((d) => d.day === day) ?? detail.days[0];
		if (!entry) return null;
		return {
			plan: pick,
			day: entry.day,
			isStarted,
			chapterTitle: entry.chapter_title,
			bookTitle: entry.book_title,
			href: `/books/${entry.book_slug}/${entry.chapter_order}?plan=${pick.slug}&day=${entry.day}`
		};
	} catch {
		return null; // plans are a bonus block — never break the homepage
	}
}

export const load: PageLoad = async ({ depends }) => {
	depends('app:lang');
	const language = getLang();
	const [books, authors, today] = await Promise.all([
		listBooks(language),
		listAuthors(),
		readingOfTheDay(language)
	]);
	return {
		books,
		featured: books.slice(0, 6),
		totalBooks: books.length,
		authors: authors.filter((a) => a.book_count > 0),
		today
	};
};
