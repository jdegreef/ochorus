<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, hreflangFor, absUrl } from '$lib/seo';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import { GLOSSARY_TERMS, byLetter, definitionOf, glossaryHref } from '$lib/glossary';
	import { i18n } from '$lib/i18n.svelte';

	const t = i18n.t;
	const path = '/glossary/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);
	const groups = byLetter();

	// English literals: the words, their definitions and this description are
	// English content (the chrome around them is catalogued).
	const title = 'Glossary of old words in the Bible and Christian classics — Ochorus';
	const description =
		'What “wherefore”, “peradventure”, “quicken” and “propitiation” mean — ' +
		`${GLOSSARY_TERMS.length} archaic and theological words from the King James Bible and the ` +
		'Christian classics, each defined in plain English with real passages from the books.';

	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.glossary'), href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	const setLd = jsonLd({
		'@context': 'https://schema.org',
		'@type': 'DefinedTermSet',
		'@id': `${canonical}#glossary`,
		name: 'Ochorus glossary of the Christian classics',
		description,
		url: canonical,
		inLanguage: 'en',
		hasDefinedTerm: GLOSSARY_TERMS.map((term) => ({
			'@type': 'DefinedTerm',
			name: term,
			description: definitionOf(term),
			url: `${SITE_URL}${glossaryHref(term)}`
		}))
	});
</script>

<Seo
	{title}
	{description}
	{canonical}
	{hreflang}
	ogImage={absUrl('/og/default.png')}
	structuredData={[crumbsLd, setLd]}
/>

<div class="page-col px-5 py-10">
	<PageHeader
		title={t('nav.glossary')}
		tagline={t('glossary.tagline')}
		meta={count}
	/>
	{#snippet count()}{t('glossary.count').replace('%count%', String(GLOSSARY_TERMS.length))}{/snippet}

	<nav class="mb-8" aria-label={t('glossary.jump')}>
		<ul class="flex flex-wrap gap-1.5">
			{#each groups as g (g.letter)}
				<li><a class="chip" href={`#letter-${g.letter}`}>{g.letter}</a></li>
			{/each}
		</ul>
	</nav>

	{#each groups as g (g.letter)}
		<section class="letter" id={`letter-${g.letter}`} aria-labelledby={`h-${g.letter}`}>
			<h2 id={`h-${g.letter}`} class="section-label">{g.letter}</h2>
			<dl class="terms">
				{#each g.terms as term (term)}
					<div class="term">
						<dt><a class="font-display text-h3" href={glossaryHref(term)} lang="en">{term}</a></dt>
						<dd class="text-small text-muted" lang="en">{definitionOf(term)}</dd>
					</div>
				{/each}
			</dl>
		</section>
	{/each}
</div>

<style>
	.letter {
		margin-bottom: 2rem;
		scroll-margin-top: calc(var(--appnav-h, 0px) + 1rem);
	}
	.terms {
		display: grid;
		gap: 0.9rem 2rem;
		margin: 0;
	}
	@media (min-width: 768px) {
		.terms {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	.term dd {
		margin: 0.15rem 0 0;
	}
	.term a {
		color: var(--color-text);
		text-decoration: none;
	}
	.term a:hover {
		color: var(--color-accent);
		text-decoration: underline;
	}
</style>
