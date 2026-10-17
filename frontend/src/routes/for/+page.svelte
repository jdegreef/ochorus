<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import Emblem from '$lib/components/Emblem.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { SITE_URL } from '$lib/config';
	import { FOR_CHROME } from '$lib/forChrome';
	import { FOR_EYEBROW, FOR_INDEX, FOR_LINKS, FOR_LOCALES, forIndexPath, forLabel, forLocale, forPath } from '$lib/forLinks';
	import { FOR_META, forIndexCard, forPhrase, forTagline } from '$lib/forMeta';
	import { lang } from '$lib/lang.svelte';
	import { track } from '$lib/analytics';
	import { PICKER_GOALS, pickerHref, type ForGoal } from '$lib/forPicker';
	import { FOR_EVENT } from '$lib/forSections';
	import { collectionPage, hreflangFor } from '$lib/seo';

	/**
	 * Who Ochorus is for: one card per "Ochorus for …" page, each in its group's
	 * accent and emblem (FOR_META), so a visitor who isn't sure which page is
	 * theirs can see them all at once. In English and French, like the pages it
	 * lists.
	 *
	 * Above the cards, two questions do the sorting for a visitor who would
	 * rather not read nine: who they read with, then what they want to do —
	 * and one link to that page's section that does it ($lib/forPicker).
	 */
	const locale = $derived(forLocale(lang.current));
	const c = $derived(FOR_CHROME[locale]);
	const card = $derived(forIndexCard(locale));
	const canonical = $derived(`${SITE_URL}${forIndexPath(locale)}`);
	const title = $derived(card.title);
	const description = $derived(c.indexDescription(FOR_LINKS.map((l) => forPhrase(l.slug, locale))));

	let role = $state<string | null>(null);
	let goal = $state<ForGoal | null>(null);
	const goals = $derived(role ? PICKER_GOALS[role][locale] : []);
	const chosen = $derived(role ? FOR_LINKS.find((l) => l.slug === role) : undefined);
	const chosenHref = $derived(
		chosen ? (goal ? pickerHref(forPath(chosen.slug, locale), goal) : forPath(chosen.slug, locale)) : ''
	);
	function pickRole(slug: string) {
		role = slug;
		goal = null;
	}

	const pageLd = $derived(
		collectionPage({
			name: title,
			description,
			url: canonical,
			items: FOR_LINKS.map((l) => ({
				name: `${FOR_EYEBROW[locale]} ${forPhrase(l.slug, locale)}`,
				url: forPath(l.slug, locale)
			}))
		})
	);
</script>

<Seo
	title="{title} — Ochorus"
	{description}
	{canonical}
	hreflang={hreflangFor(FOR_INDEX, [...FOR_LOCALES])}
	ogImage="{SITE_URL}/og/for/{locale === 'en' ? '' : `${locale}/`}index.png"
	ogImageAlt={title}
	ogImageWidth={1200}
	ogImageHeight={630}
	structuredData={[pageLd]}
/>

<div class="page-col px-5 py-10" lang={locale}>
	<header class="max-w-2xl">
		<p class="eyebrow text-gold">{FOR_EYEBROW[locale]}</p>
		<h1 class="mt-2 text-balance font-display text-h1 font-semibold leading-tight">{title}</h1>
		<p class="mt-4 text-body text-muted">{c.indexLead}</p>
	</header>

	<!-- Two taps instead of nine cards: who, then what — one link to the right
	     section of the right page. -->
	<section class="picker mt-8 rounded-card border border-border bg-surface p-5 sm:p-6" aria-labelledby="picker-heading">
		<h2 id="picker-heading" class="text-h3">{c.picker.heading}</h2>
		<p class="mt-4 text-eyebrow text-muted" id="picker-who">{c.picker.who}</p>
		<div class="mt-2 flex flex-wrap gap-1.5" role="group" aria-labelledby="picker-who">
			{#each FOR_LINKS as l (l.slug)}
				<button
					type="button"
					class="chip"
					class:active={role === l.slug}
					aria-pressed={role === l.slug}
					onclick={() => pickRole(l.slug)}>{c.picker.roles[l.slug]}</button
				>
			{/each}
		</div>
		{#if chosen}
			<p class="mt-5 text-eyebrow text-muted" id="picker-what">{c.picker.what}</p>
			<div class="mt-2 flex flex-wrap gap-1.5" role="group" aria-labelledby="picker-what">
				{#each goals as g (g)}
					<button type="button" class="chip" class:active={goal === g} aria-pressed={goal === g} onclick={() => (goal = g)}
						>{c.picker.goals[g]}</button
					>
				{/each}
			</div>
			<a
				class="btn btn-primary mt-5"
				href={chosenHref}
				onclick={() => track(FOR_EVENT, { group: chosen.slug, action: `picker-${goal ?? 'page'}` })}
				>{c.picker.go(forPhrase(chosen.slug, locale))} <Arrow /></a
			>
		{/if}
	</section>

	<ul class="groups mt-10">
		{#each FOR_LINKS as l (l.slug)}
			{@const meta = FOR_META[l.slug]}
			<li>
				<a class="group group-wash card-lift" href={forPath(l.slug, locale)} style="--group: {meta.accent}">
					<span class="badge emblem-chip group-chip"><Emblem name={meta.emblem} /></span>
					<span class="min-w-0">
						<span class="block text-h3 font-semibold text-text">{forLabel(l, locale)}</span>
						<span class="mt-1 block text-small text-muted">{forTagline(l.slug, locale)}</span>
						<span class="group-ink mt-3 inline-block text-small font-semibold"
							>{FOR_EYEBROW[locale]} {forPhrase(l.slug, locale)} <Arrow /></span
						>
					</span>
				</a>
			</li>
		{/each}
	</ul>
</div>

<style>
	.groups {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 1rem;
	}
	.group {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
		height: 100%;
		padding: 1.25rem;
		border-radius: var(--radius-card);
	}
	.group:hover {
		text-decoration: none;
		border-color: color-mix(in srgb, var(--group) 50%, var(--color-border));
	}
	.badge {
		--chip-size: 3.25rem;
	}
	@media (max-width: 1023.98px) {
		.groups {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (max-width: 639.98px) {
		.groups {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
