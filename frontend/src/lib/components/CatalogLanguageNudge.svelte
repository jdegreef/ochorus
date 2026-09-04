<script lang="ts">
	import { onMount } from 'svelte';
	import { lang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { listBooks, listSermons, listPlans, listTopics, listAuthors } from '$lib/library-public';

	/**
	 * On a minority-language catalog page, gently point the reader to the fuller
	 * English library — a stopgap for the fact that content is mostly English and
	 * a locale's list can look near-empty until translations land. It only appears
	 * when English genuinely has *more* items than the current locale, so a
	 * complete locale catalog (e.g. once Spanish is filled in) never sees it.
	 *
	 * Deliberately narrow: this doesn't change routing, prerendering, SEO or the
	 * content model — it's a client-side nudge that switches the reader to English
	 * (UI + content) if they choose. A true UI/reading-language split is a separate
	 * design decision.
	 */
	let {
		kind,
		localizedCount
	}: { kind: 'books' | 'sermons' | 'plans' | 'topics' | 'authors'; localizedCount: number } =
		$props();

	const t = i18n.t;

	// English count is fetched client-side (so nothing extra is prerendered) and
	// only for non-English UIs — English readers already see the full catalog.
	let englishCount = $state<number | null>(null);
	onMount(async () => {
		if (lang.current === 'en') return;
		const fetchers = {
			books: listBooks,
			sermons: listSermons,
			plans: listPlans,
			topics: listTopics,
			authors: listAuthors
		} as const;
		try {
			englishCount = (await fetchers[kind]('en')).length;
		} catch {
			/* offline / API down — no nudge */
		}
	});

	const show = $derived(
		lang.current !== 'en' && englishCount !== null && englishCount > localizedCount
	);
</script>

{#if show}
	<div
		class="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-card border border-accent-soft-border bg-accent-soft px-4 py-3"
	>
		<span class="text-small text-text">{t('catalog.moreInEnglish')}</span>
		<button class="btn btn-ghost py-1.5 whitespace-nowrap" onclick={() => lang.choose('en')}>
			{t('catalog.browseEnglish')}
		</button>
	</div>
{/if}
