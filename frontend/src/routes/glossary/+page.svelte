<script lang="ts">
	import { SITE_URL } from '$lib/config';
	import { jsonLd, breadcrumbLd, hreflangFor, absUrl } from '$lib/seo';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import {
		FAITH_WORDS,
		GLOSSARY_TERMS,
		KEY_WORDS,
		OLD_WORDS,
		byLetter,
		definitionOf,
		findTerms,
		glossaryHref,
		headOf,
		wordOfTheDay
	} from '$lib/glossary';
	import { dayIndex } from '$lib/quoteText';
	import { i18n } from '$lib/i18n.svelte';
	import { onMount } from 'svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	// The word of the day: the build day's in the prerendered page, re-taken
	// for the reader's own day after mount (the featured quote's rule).
	let day = $state(dayIndex(new Date(), GLOSSARY_TERMS.length));
	onMount(() => {
		day = dayIndex(new Date(), GLOSSARY_TERMS.length);
	});
	const today = $derived(wordOfTheDay(day));
	const todayHead = $derived(headOf(today));
	const shelves = [
		{ id: 'old', k: 'glossary.oldWords', note: 'glossary.oldWordsNote', terms: OLD_WORDS },
		{ id: 'faith', k: 'glossary.faithWords', note: 'glossary.faithWordsNote', terms: FAITH_WORDS }
	];

	const t = i18n.t;
	const path = '/glossary/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);
	const groups = byLetter();

	// Find as you type. The full A–Z stays in the prerendered page (the crawl's
	// way to every word); a query swaps it for the matches, in the browser only.
	let query = $state('');
	const matches = $derived(findTerms(query));
	const searching = $derived(query.trim() !== '');

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

	<!-- Find as you type, first: a reader who came for one word goes straight
	     to it. A query swaps the whole page below for its matches. -->
	<div class="find mb-8">
		<label for="glossary-find" class="eyebrow text-muted">{t('glossary.find')}</label>
		<input
			id="glossary-find"
			type="search"
			class="filter-field mt-1.5 w-full max-w-md"
			placeholder={t('glossary.findPlaceholder')}
			autocomplete="off"
			spellcheck="false"
			bind:value={query}
		/>
		<p class="mt-1.5 text-small text-muted" aria-live="polite">
			{#if searching}
				{matches.length
					? t('glossary.matches').replace('%n%', String(matches.length))
					: t('glossary.noMatch').replace('%q%', query.trim())}
			{/if}
		</p>
	</div>

	{#if searching}
		<dl class="terms mb-10">
			{#each matches as term (term)}
				<div class="term">
					<dt><a class="font-display text-h3" href={glossaryHref(term)} lang="en">{term}</a></dt>
					<dd class="text-small text-muted" lang="en">{definitionOf(term)}</dd>
				</div>
			{/each}
		</dl>
	{:else}
	<!-- One word first, set as a dictionary entry: the page's promise. -->
	<section class="wotd mb-10" aria-labelledby="wotd-label">
		<p id="wotd-label" class="eyebrow wotd-label">{t('glossary.wordOfDay')}</p>
		<p class="mt-2" lang="en">
			<a class="wotd-term font-display" href={glossaryHref(today)}>{today}</a>
			{#if todayHead}<span class="wotd-say">/{todayHead.say}/</span>
				<span class="wotd-pos">{todayHead.pos}</span>{/if}
		</p>
		<p class="wotd-def mt-2 max-w-2xl" lang="en">{definitionOf(today)}</p>
		<a class="mt-3 inline-block text-small font-semibold" href={glossaryHref(today)}
			>{t('glossary.seeWord')} <Arrow /></a
		>
	</section>

	<!-- The ten words a new believer meets first, numbered: a short course
	     rather than another shelf to browse. -->
	{#if KEY_WORDS.length}
		<section class="ten mb-10" aria-labelledby="ten-words">
			<h2 id="ten-words" class="font-display text-h3 font-semibold">{t('glossary.tenWords')}</h2>
			<p class="mt-0.5 text-small text-muted">{t('glossary.tenWordsNote')}</p>
			<ol class="ten-list mt-4" lang="en">
				{#each KEY_WORDS as w, i (w)}
					<li>
						<span class="ten-num" aria-hidden="true">{i + 1}</span>
						<span>
							<a class="ten-term font-display" href={glossaryHref(w)}>{w}</a>
							<span class="block text-small text-muted">{definitionOf(w)}</span>
						</span>
					</li>
				{/each}
			</ol>
		</section>
	{/if}

	<!-- The two kinds of word the glossary holds, each a shelf of its own. -->
	{#if OLD_WORDS.length && FAITH_WORDS.length}
		<div class="shelves mb-12">
			{#each shelves as sh (sh.id)}
				<section class="shelf" aria-labelledby="shelf-{sh.id}">
					<h2 id="shelf-{sh.id}" class="font-display text-h3 font-semibold">{t(sh.k)}</h2>
					<p class="mt-0.5 text-small text-muted">{t(sh.note)}</p>
					<ul class="shelf-words mt-3" lang="en">
						{#each sh.terms as w (w)}
							<li><a href={glossaryHref(w)}>{w}</a></li>
						{/each}
					</ul>
				</section>
			{/each}
		</div>
	{/if}

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
	{/if}
</div>

<style>
	.wotd {
		padding: 1.5rem 1.75rem;
		border: 1px solid var(--color-border);
		border-block-start: 3px solid var(--color-gold);
		border-radius: var(--radius-card);
		background: var(--color-surface);
	}
	.wotd-label {
		color: var(--color-gold);
	}
	.wotd-term {
		font-size: var(--fs-display);
		font-weight: 600;
		line-height: 1.05;
		color: var(--color-text);
		text-decoration: none;
	}
	.wotd-term:hover {
		color: var(--color-accent);
	}
	.wotd-say {
		margin-inline-start: 0.75rem;
		font-size: var(--fs-h3);
		color: var(--color-muted);
	}
	.wotd-pos {
		margin-inline-start: 0.5rem;
		font-family: var(--font-display, Georgia, serif);
		font-style: italic;
		color: var(--color-accent);
	}
	.wotd-def {
		font-family: var(--font-display, Georgia, serif);
		font-size: var(--fs-h3);
		line-height: 1.45;
	}
	.ten {
		padding: 1.25rem 1.5rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
	}
	.ten-list {
		display: grid;
		gap: 0.75rem 2rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	@media (min-width: 768px) {
		.ten-list {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	.ten-list li {
		display: flex;
		gap: 0.75rem;
		align-items: baseline;
	}
	.ten-num {
		flex: none;
		inline-size: 1.5rem;
		text-align: end;
		font-family: var(--font-display, Georgia, serif);
		font-weight: 600;
		color: var(--color-gold);
	}
	.ten-term {
		font-size: var(--fs-h3);
		font-weight: 600;
		color: var(--color-text);
		text-decoration: none;
	}
	.ten-term:hover {
		color: var(--color-accent);
		text-decoration: underline;
	}
	.shelves {
		display: grid;
		gap: 1.25rem;
	}
	@media (min-width: 768px) {
		.shelves {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	.shelf {
		padding: 1.1rem 1.25rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
	}
	.shelf-words {
		display: flex;
		flex-wrap: wrap;
		gap: 0.2rem 0.8rem;
		list-style: none;
		margin: 0;
		padding: 0;
		font-family: var(--font-display, Georgia, serif);
	}
	.shelf-words a {
		color: var(--color-text);
		text-decoration: none;
	}
	.shelf-words a:hover {
		color: var(--color-accent);
		text-decoration: underline;
	}
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
