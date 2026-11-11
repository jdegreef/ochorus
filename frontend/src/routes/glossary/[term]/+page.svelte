<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, hreflangFor, absUrl } from '$lib/seo';
	import Arrow from '$lib/components/Arrow.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { definitionOf, glossaryHref, relatedTerms, titleCase } from '$lib/glossary';
	import type { WordPassage } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';

	let { data } = $props();
	const t = i18n.t;
	const term = $derived<string>(data.term);
	const passages = $derived<WordPassage[]>(data.passages);
	const definition = $derived(definitionOf(term));
	const related = $derived(relatedTerms(term));

	const path = $derived(glossaryHref(term));
	const canonical = $derived(`${SITE_URL}${path}`);
	const hreflang = $derived(hreflangFor(path, ['en']));

	// English literals: the word, its definition and the passages are English
	// content; the chrome around them is catalogued.
	const title = $derived(`${titleCase(term)} — meaning in the Bible and Christian classics — Ochorus`);
	const description = $derived(
		`What does “${term}” mean? ${definition} ` +
			(passages.length
				? `With ${passages.length === 1 ? 'a real passage' : 'real passages'} from ${[...new Set(passages.map((p) => p.author.name))].join(', ')}.`
				: 'From the Ochorus glossary of the Christian classics.')
	);

	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.glossary'), href: '/glossary/' },
		{ name: term, href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	const termLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'DefinedTerm',
			name: term,
			description: definition,
			url: canonical,
			inLanguage: 'en',
			inDefinedTermSet: {
				'@type': 'DefinedTermSet',
				'@id': `${SITE_URL}/glossary/#glossary`,
				name: 'Ochorus glossary of the Christian classics',
				url: `${SITE_URL}/glossary/`
			}
		})
	);
</script>

<Seo
	{title}
	{description}
	{canonical}
	{hreflang}
	ogImage={absUrl('/og/default.png')}
	structuredData={[crumbsLd, termLd]}
/>

<div class="page-col px-5 py-10">
	<Breadcrumb items={crumbs} />

	<header class="mb-8">
		<p class="eyebrow text-muted">{t('nav.glossary')}</p>
		<h1 class="text-h1" lang="en">{term}</h1>
		<p class="definition mt-3 max-w-2xl" lang="en">{definition}</p>
	</header>

	{#if passages.length}
		<section class="mb-10" aria-labelledby="in-classics">
			<h2 id="in-classics" class="section-label">{t('glossary.inClassics')}</h2>
			<ol class="passages">
				{#each passages as p (p.href)}
					<li class="passage">
						<!-- Real sentences from the library that use the word, each
						     linked to its paragraph (backend library.word_passages). -->
						<p class="excerpt" lang="en">{p.before}<mark>{p.match}</mark>{p.after}</p>
						<a class="who" href={p.href}>
							<span class="whitespace-nowrap">{p.author.name}</span>
							<span class="sep mx-1">·</span>
							<cite>{p.work}</cite>{#if p.title && p.title !== p.work}<span class="sep mx-1">·</span><span>{p.title}</span>{/if}
							<Arrow />
						</a>
					</li>
				{/each}
			</ol>
		</section>
	{/if}

	{#if related.length}
		<section class="mb-10" aria-labelledby="related">
			<h2 id="related" class="section-label">{t('glossary.related')}</h2>
			<ul class="flex flex-wrap gap-2">
				{#each related as r (r)}
					<li><a class="chip" href={glossaryHref(r)} lang="en">{r}</a></li>
				{/each}
			</ul>
		</section>
	{/if}

	<p class="mt-8 text-small">
		<a href="/glossary/">{t('glossary.all')} <Arrow /></a>
	</p>
</div>

<style>
	.definition {
		font-family: var(--font-display, Georgia, serif);
		font-size: var(--fs-h3);
		line-height: 1.45;
		color: var(--color-text);
	}
	.passages {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.9rem;
		max-width: 48rem;
	}
	.passage {
		padding: 0.9rem 1.1rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
	}
	.excerpt {
		margin: 0 0 0.5rem;
		font-family: var(--font-display, Georgia, serif);
		line-height: 1.5;
		color: var(--color-text);
	}
	mark {
		color: var(--color-text);
		background: color-mix(in srgb, var(--color-gold) 22%, transparent);
		border-radius: 2px;
		padding: 0 1px;
	}
	.who {
		font-size: var(--fs-small);
		color: var(--color-muted);
		text-decoration: none;
	}
	.who:hover {
		color: var(--color-accent);
		text-decoration: underline;
	}
</style>
