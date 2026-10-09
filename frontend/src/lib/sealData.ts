import { allProgress } from './progress';
import { libraryBooks } from './resumeBooks';
import { listPlans } from './library-public';
import { planProgress } from './planProgress.svelte';
import { readingActivity } from './readingActivity.svelte';
import { marks } from './marks.svelte';
import { eraById } from './eras';
import { localizeHref } from './href';
import { i18n } from './i18n.svelte';
import type { Seal, SealFamily, SealId, SealInput } from './seals';

/**
 * The browser side of reading seals: gathering what `computeSeals` reads from
 * the device's stores, and the words a seal is shown with. `seals.ts` stays
 * pure; this is the one place that knows where each input lives.
 */

/** Everything a seal is worked out from, for the reader's language, and the
 *  titles of the books and plans that earned one (keyed `kind:slug`). The two
 *  fetched lists (books for authors and eras, plans for their lengths) fall
 *  back to empty, so a seal that needs them simply stays on its way. */
export async function loadSealInput(lang: string): Promise<{ input: SealInput; titles: Map<string, string> }> {
	const [books, plans] = await Promise.all([
		libraryBooks(lang).catch(() => []),
		listPlans(lang).catch(() => [])
	]);
	const planDone: Record<string, number[]> = {};
	for (const p of plans) {
		const done = planProgress.doneDays(p.slug);
		if (done.length) planDone[p.slug] = done;
	}
	const markIds = new Set<string>();
	for (const g of marks.allByEdition(lang)) for (const m of g.marks) markIds.add(m.id);
	const titles = new Map<string, string>([
		...books.map((b) => [`book:${b.slug}`, b.title] as const),
		...plans.map((p) => [`plan:${p.slug}`, p.title] as const)
	]);
	const input: SealInput = {
		progress: allProgress(),
		books: books.map((b) => ({ slug: b.slug, author: b.author })),
		days: readingActivity.days(),
		plans: plans.map((p) => ({ slug: p.slug, day_count: p.day_count })),
		planDone,
		marks: markIds.size
	};
	return { input, titles };
}

const camel = (id: string) => id.charAt(0).toUpperCase() + id.slice(1);

export function sealName(seal: Seal): string {
	const t = i18n.t;
	return seal.id === 'pupil' && seal.author
		? t('seals.pupilOf').replace('%name%', seal.author.name)
		: t(`seals.name${camel(seal.id)}`);
}

export const sealRule = (id: SealId): string => i18n.t(`seals.rule${camel(id)}`);
export const sealFamily = (f: SealFamily): string => i18n.t(`seals.family${camel(f)}`);

/** Where a seal points onward: always somewhere to read next. */
export function sealNext(seal: Seal): { href: string; label: string } {
	const t = i18n.t;
	if (seal.id === 'pupil' && seal.author)
		return {
			href: localizeHref(`/authors/${seal.author.slug}`),
			label: t('seals.nextAuthor').replace('%name%', seal.author.name)
		};
	if (seal.id === 'centuries' && seal.missingEras?.length) {
		const era = eraById(seal.missingEras[0])!;
		return {
			href: localizeHref(`/biographies/era/${era.id}`),
			label: t('seals.nextEra').replace('%era%', t(era.k))
		};
	}
	if (seal.id === 'pilgrim') return { href: localizeHref('/plans'), label: t('seals.nextPlans') };
	if (seal.id === 'margins') return { href: localizeHref('/notebook'), label: t('seals.nextNotebook') };
	if (seal.id === 'hearer') return { href: localizeHref('/sermons'), label: t('seals.nextSermons') };
	return { href: localizeHref('/books'), label: t('seals.nextBooks') };
}
