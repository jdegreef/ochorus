<script lang="ts">
	import Arrow from '$lib/components/Arrow.svelte';
	import Emblem from '$lib/components/Emblem.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { SITE_URL } from '$lib/config';
	import { FOR_META } from '$lib/emblemNames';
	import { FOR_INDEX, FOR_LINKS, forPath, forPhrase } from '$lib/forLinks';
	import { collectionPage, hreflangFor } from '$lib/seo';

	/**
	 * Who Ochorus is for: one card per "Ochorus for …" page, each in its group's
	 * accent and emblem (FOR_META), so a visitor who isn't sure which page is
	 * theirs can see them all at once. English-only, like the pages it lists.
	 */
	const canonical = `${SITE_URL}${FOR_INDEX}`;
	const title = 'Who Ochorus is for';
	const description =
		'Free Christian classics for churches, small groups, youth ministries, missionaries, chaplains, Bible colleges, schools, homeschool families and parents.';
	const pageLd = collectionPage({
		name: title,
		description,
		url: canonical,
		items: FOR_LINKS.map((l) => ({ name: `Ochorus for ${forPhrase(l.label)}`, url: forPath(l.slug) }))
	});
</script>

<Seo
	title="{title} — Ochorus"
	{description}
	{canonical}
	hreflang={hreflangFor(FOR_INDEX, ['en'])}
	ogImage="{SITE_URL}/og/for/index.png"
	ogImageAlt={title}
	ogImageWidth={1200}
	ogImageHeight={630}
	structuredData={[pageLd]}
/>

<div class="page-col px-5 py-10" lang="en">
	<header class="max-w-2xl">
		<p class="eyebrow text-gold">Ochorus for</p>
		<h1 class="mt-2 text-balance font-display text-h1 font-semibold leading-tight">{title}</h1>
		<p class="mt-4 text-body text-muted">
			A free library of the great Christian classics, with no ads, no paywall and no account needed. Here is
			what it offers each of the people who use it: plans to read together, books to start with, printable
			guides and books to take offline.
		</p>
	</header>

	<ul class="groups mt-10">
		{#each FOR_LINKS as l (l.slug)}
			{@const meta = FOR_META[l.slug]}
			<li>
				<a class="group card-lift" href={forPath(l.slug)} style="--group: {meta.accent}">
					<span class="badge emblem-chip"><Emblem name={meta.emblem} /></span>
					<span class="min-w-0">
						<span class="block text-h3 font-semibold text-text">{l.label}</span>
						<span class="mt-1 block text-small text-muted">{l.tagline}</span>
						<span class="go mt-3 inline-block text-small font-semibold">Ochorus for {forPhrase(l.label)} <Arrow /></span>
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
		border: 1px solid color-mix(in srgb, var(--group) 22%, var(--color-border));
		background:
			radial-gradient(90% 130% at 0% 0%, color-mix(in srgb, var(--group) 14%, transparent), transparent 60%),
			color-mix(in srgb, var(--group) 5%, var(--color-surface));
	}
	.group:hover {
		text-decoration: none;
		border-color: color-mix(in srgb, var(--group) 50%, var(--color-border));
	}
	.badge {
		--chip-hue: var(--group);
		--chip-size: 3.25rem;
	}
	.go {
		color: color-mix(in srgb, var(--group) 80%, var(--color-text));
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
