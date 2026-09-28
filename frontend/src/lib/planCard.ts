// Read by the build script under plain Node, so this module stays import-free
// at runtime: the one import below is a type, and Node strips it.
import type { PlanDetail } from './library-public';

/**
 * Where a reading plan's share card lives, per interface language.
 *
 * Not committed: `scripts/build-plan-cards.mjs` draws one into the build for
 * every prerendered plan page, from the data that page was rendered with. Plans
 * are per-language rows, and the card's words are the page's own, so there is
 * one per language. Said once so the page that names a card and the script
 * that draws it cannot disagree.
 */
export function planCardUrl(slug: string, language: string): string {
	return `/og/plans/${language}/${slug}.jpg`;
}

const FETCHED =
	/<script type="application\/json" data-sveltekit-fetched data-url="[^"]*\/api\/library\/plans\/[^"/?]+\/\?language=([^"&]+)"[^>]*>([\s\S]*?)<\/script>/g;

/**
 * The plan a prerendered plan page was rendered from, and the language that
 * answered — every inlined response is tried, since a language with no row
 * 404s first and the page falls back. Null when the page holds no plan.
 */
export function planData(html: string): { plan: PlanDetail; language: string } | null {
	for (const [, language, raw] of html.matchAll(FETCHED)) {
		try {
			const response = JSON.parse(raw);
			const plan = JSON.parse(response.body);
			if ((response.status ?? 200) < 400 && plan?.slug && plan?.title) return { plan, language };
		} catch {
			/* not this one */
		}
	}
	return null;
}

/**
 * Minutes a day, as the plans shelf shows it before it knows a reader's own
 * pace: `readingPace`'s DEFAULT_WPM (200), whole minutes, at least one. A share
 * image has no reader, so it keeps the default rather than anyone's pace.
 */
export function minutesPerDay(plan: { total_words: number; day_count: number }): number {
	return plan.day_count ? Math.max(1, Math.round(plan.total_words / plan.day_count / 200)) : 0;
}
