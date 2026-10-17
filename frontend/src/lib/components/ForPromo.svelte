<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import { track } from '$lib/analytics';
	import { FOR_EYEBROW, forIndexPath, forPath } from '$lib/forLinks';
	import { forPhrase } from '$lib/forMeta';
	import { FOR_PROMOS, PROMO_LEAD, PROMO_WORDS, promoLocale, type ForPlace } from '$lib/forPromos';
	import { FOR_EVENT, type ForSection } from '$lib/forSections';
	import { lang } from '$lib/lang.svelte';

	/**
	 * One quiet line pointing a leader at their "Ochorus for …" page from
	 * wherever they are — "Reading this with a group? See Ochorus for small
	 * groups or churches →" — from the table in $lib/forPromos. `place` picks
	 * the question and the pages; a topic or a search passes its own `slugs`.
	 * With `index`, it points at the page listing every group instead. Shown
	 * only where the pages are written (English, French), like the footer row.
	 */
	let {
		place,
		slugs,
		section,
		index = false,
		class: cls = ''
	}: {
		place?: ForPlace;
		slugs?: string[];
		section?: ForSection;
		index?: boolean;
		class?: string;
	} = $props();

	const locale = $derived(promoLocale(lang.current));
	const promo = $derived(place && place in FOR_PROMOS ? FOR_PROMOS[place as keyof typeof FOR_PROMOS] : undefined);
	const groups = $derived(slugs ?? promo?.slugs ?? []);
	const anchor = $derived(section ?? promo?.section);
	/** The page names as runs of text, with the language's own "or" between. */
	const parts = $derived.by(() => {
		if (!locale || index) return [];
		let i = 0;
		return new Intl.ListFormat(locale, { type: 'disjunction' })
			.formatToParts(groups.map((s) => forPhrase(s, locale)))
			.map((p) => (p.type === 'element' ? { text: p.value, slug: groups[i++] } : { text: p.value }));
	});
	const report = (group: string) => track(FOR_EVENT, { group, action: `promo-${place ?? 'index'}` });
</script>

{#if locale && (index || parts.length)}
	<p class="for-promo text-small text-muted {cls}" lang={locale}>
		{#if index}
			{PROMO_WORDS[locale].allLead}
			<a class="font-semibold text-accent hover:underline" href={forIndexPath(locale)} onclick={() => report('index')}
				>{PROMO_WORDS[locale].all} <Arrow /></a
			>
		{:else}
			{place ? PROMO_LEAD[locale][place] : ''}
			{PROMO_WORDS[locale].see}
			{#each parts as part, i (i)}{#if part.slug}<a
						class="font-semibold text-accent hover:underline"
						href="{forPath(part.slug, locale)}{anchor ? `#${anchor}` : ''}"
						onclick={() => report(part.slug)}
						>{#if i === 0}{FOR_EYEBROW[locale]}{' '}{/if}{part.text}</a
					>{:else}{part.text}{/if}{/each}
			<Arrow />
		{/if}
	</p>
{/if}
