<script lang="ts">
	import { goto } from '$app/navigation';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { searchHref } from '$lib/searchState';
	import { toBookTile, type CoverFace } from '$lib/library-public';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import Icon from '$lib/components/Icon.svelte';

	/**
	 * The logged-out home's hero (HomeMarketing): what the reader gets, said
	 * in one line, beside three of the library's own covers — design review
	 * #5 — whole, so each title reads, and each a link to its book. One
	 * search field, one solid "Start reading", About as a text link, and the
	 * trust line as one muted line of words.
	 *
	 * The covers sit at the inline end on a wide screen and under the words on
	 * a phone, where the padding is trimmed so the top of the spread shows in
	 * the first screen. They come from the build's home snapshot (`hero`,
	 * `$lib/homeShelves`), so the prerendered HTML and its hydration draw the
	 * same three and no extra request is made for them.
	 */
	let { covers }: { covers: CoverFace[] } = $props();
	const t = i18n.t;

	// Three make the spread; a language with fewer painted books gets the
	// deck (the snapshot holds exactly what shows).
	const tiles = $derived(covers.map(toBookTile));

	// Search → the full search page. Progressive enhancement: the form is a
	// real GET to /search (works with no JS); with JS we intercept and navigate
	// client-side so it stays in the SPA.
	let query = $state('');
	function submitSearch(e: Event) {
		e.preventDefault();
		goto(localizeHref(searchHref(query)));
	}

	const trust = [t('home.proofFree'), t('home.proofNoAds'), t('home.proofOffline')];
</script>

<section class="page-col px-5 pt-8 sm:pt-16">
	<div class="intro">
		<div class="min-w-0">
			<h1 class="text-display mb-4 max-w-xl">{t('home.heroTitle')}</h1>
			<p class="mb-6 max-w-lg text-body text-muted">{t('home.heroTagline')}</p>
			<form
				onsubmit={submitSearch}
				method="GET"
				action={localizeHref('/search')}
				role="search"
				class="mb-5 flex max-w-lg items-center rounded-full border border-border-strong bg-surface py-1 pe-1 ps-4 shadow-sm focus-within:border-accent"
			>
				<!-- The pill is the field (the input inside is bare), so it wears
				     .field's --border-strong edge like the nav search. The glass at
				     its end is the submit: one field, no second "Search" button
				     beside the one primary below. -->
				<input
					bind:value={query}
					name="q"
					type="search"
					enterkeyhint="search"
					placeholder={t('search.placeholder')}
					aria-label={t('nav.search')}
					class="min-w-0 flex-1 bg-transparent py-1 text-body text-text placeholder:text-muted focus-visible:-outline-offset-2 max-sm:placeholder:text-small"
				/>
				<button type="submit" class="btn btn-icon shrink-0 rounded-full text-muted hover:text-accent" aria-label={t('nav.search')}>
					<Icon name="search" size={20} />
				</button>
			</form>
			<!-- The one primary on the view: into the library. About is a way to
			     read about Ochorus, not a rival call, so it is a text link. -->
			<div class="flex flex-wrap items-center gap-x-6 gap-y-3">
				<a href={localizeHref('/books')} class="btn btn-primary btn-solid">{t('home.startReading')}</a>
				<a href={localizeHref('/about')} class="text-body font-semibold">{t('home.aboutOchorus')}</a>
			</div>
			<p class="mt-5 text-small text-muted">
				{#each trust as label, i (label)}{#if i}<span class="sep trust-sep" aria-hidden="true">·</span>{/if}{label}{/each}
			</p>
		</div>
		{#if tiles.length}
			<!-- The covers are a picture of the library and a way into it: each
			     links to its own book, labelled with its title and author. -->
			<div class="intro-fan">
				<CoverStrip covers={tiles} size="spread" priority />
			</div>
		{/if}
	</div>
</section>

<style>
	.intro {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 1.75rem;
		align-items: center;
	}
	.intro-fan {
		display: block;
		width: min(100%, 24rem);
		margin-inline: auto;
	}
	@media (min-width: 768px) {
		.intro {
			grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
			gap: 3rem;
		}
		.intro-fan {
			width: min(100%, 34rem);
		}
	}
	/* The hero's one loud control — solid accent, as the footer's invite is
	   (STYLE_GUIDE §5 names both exceptions): the first screen has one thing
	   to do, so it says so. Scoped, so every other .btn-primary stays soft. */
	.trust-sep {
		margin-inline: 0.5em;
	}
</style>
