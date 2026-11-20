<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, hreflangFor, absUrl } from '$lib/seo';
	import Arrow from '$lib/components/Arrow.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { definitionOf, glossaryHref, headOf, relatedTerms, titleCase, wordFamily } from '$lib/glossary';
	import type { WordPassage, WordVerse } from '$lib/library-public';
	import Portrait from '$lib/components/Portrait.svelte';
	import { i18n } from '$lib/i18n.svelte';

	let { data } = $props();
	const t = i18n.t;
	const term = $derived<string>(data.term);
	const passages = $derived<WordPassage[]>(data.passages);
	const definition = $derived(definitionOf(term));
	const verses = $derived<WordVerse[]>(data.verses ?? []);
	const head = $derived(headOf(term));
	// The word's family on its own row; the neighbours in the curated order
	// (the same theme) after it.
	const family = $derived(wordFamily(term));
	const related = $derived(relatedTerms(term).filter((r) => !family.includes(r)));

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
		<!-- The dictionary head: how it is said, what it is, where it came
		     from (glossaryHeads.json — a first draft, for checking). -->
		{#if head}
			<p class="head mt-1" lang="en">
				<span class="say">/{head.say}/</span>
				<span class="pos">{head.pos}</span>
			</p>
		{/if}
		<p class="definition mt-3 max-w-2xl" lang="en">{definition}</p>
		{#if head?.origin}
			<p class="origin mt-3 max-w-2xl text-small text-muted" lang="en">
				<span class="font-semibold">{t('glossary.origin')}</span>
				{head.origin}
			</p>
		{/if}
	</header>

	{#if verses.length}
		<!-- The word in the library's own Bible (the Open Word Bible), each
		     verse opening its chapter there. -->
		<section class="mb-10" aria-labelledby="in-bible">
			<h2 id="in-bible" class="section-label">{t('glossary.inBible')}</h2>
			<ol class="passages">
				{#each verses as v (v.ref)}
					<li class="passage verse">
						<p class="excerpt" lang="en">{v.before}<mark>{v.match}</mark>{v.after}</p>
						{#if v.href}
							<a class="who" href={v.href}><span class="font-semibold">{v.ref}</span><span class="sep mx-1">·</span>Open Word Bible <Arrow /></a>
						{:else}
							<span class="who"><span class="font-semibold">{v.ref}</span><span class="sep mx-1">·</span>Open Word Bible</span>
						{/if}
					</li>
				{/each}
			</ol>
		</section>
	{/if}

	{#if passages.length}
		<section class="mb-10" aria-labelledby="in-classics">
			<h2 id="in-classics" class="section-label">{t('glossary.inClassics')}</h2>
			<ol class="passages">
				{#each passages as p (p.href)}
					<li class="passage with-face">
						<!-- Real sentences from the library that use the word, each
						     linked to its paragraph (backend library.word_passages),
						     beside the face of the writer who used it. -->
						<Portrait
							slug={p.author.slug}
							name={p.author.name}
							url={p.author.photo_url}
							px={48}
							decorative
							class="h-12 w-12"
							initialsClass="text-small"
						/>
						<div class="min-w-0">
						<p class="excerpt" lang="en">{p.before}<mark>{p.match}</mark>{p.after}</p>
						<a class="who" href={p.href}>
							<span class="whitespace-nowrap">{p.author.name}</span>
							<span class="sep mx-1">·</span>
							<cite>{p.work}</cite>{#if p.title && p.title !== p.work}<span class="sep mx-1">·</span><span>{p.title}</span>{/if}
							<Arrow />
						</a>
						</div>
					</li>
				{/each}
			</ol>
		</section>
	{/if}

	{#if family.length}
		<section class="mb-10" aria-labelledby="family">
			<h2 id="family" class="section-label">{t('glossary.family')}</h2>
			<ul class="flex flex-wrap gap-2">
				{#each family as r (r)}
					<li><a class="chip" href={glossaryHref(r)} lang="en">{r}</a></li>
				{/each}
			</ul>
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
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.25rem 0.9rem;
	}
	.say {
		font-size: var(--fs-h3);
		color: var(--color-muted);
	}
	.pos {
		font-family: var(--font-display, Georgia, serif);
		font-style: italic;
		color: var(--color-accent);
	}
	.with-face {
		display: flex;
		gap: 0.9rem;
		align-items: flex-start;
	}
	.verse {
		border-inline-start: 3px solid var(--color-gold);
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
