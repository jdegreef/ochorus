<script lang="ts">
	import { goto } from '$app/navigation';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { searchHref } from '$lib/searchState';
	import { toBookTile, type CoverFace } from '$lib/library-public';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import { lang } from '$lib/lang.svelte';
	import { footerLocales } from '$lib/footerLocales';
	import { isUnmodifiedPrimaryClick } from '$lib/plainClick';
	import { heroSearch } from '$lib/heroSearch.svelte';
	import { localizeHref as localeHome, getTextDirection, type locales } from '$lib/paraglide/runtime';
	import { onMount } from 'svelte';

	/**
	 * The logged-out home's hero (HomeMarketing): what the reader gets, said
	 * in one line, beside three of the library's own covers — design review
	 * #5 — whole, so each title reads, and each a link to its book. One
	 * search field, the languages under it, one solid "Browse the Library",
	 * today's reading as a text link, then the library's counts over the
	 * muted trust line (design review 2026-11, #3–#6).
	 *
	 * The covers sit at the inline end on a wide screen and under the words on
	 * a phone, where the padding is trimmed so the top of the spread shows in
	 * the first screen. They come from the build's home snapshot (`hero`,
	 * `$lib/homeShelves`), so the prerendered HTML and its hydration draw the
	 * same three and no extra request is made for them.
	 */
	let {
		covers,
		counts = { books: 0, sermons: 0 }
	}: { covers: CoverFace[]; counts?: { books: number; sermons: number } } = $props();
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

	// "In your language", shown rather than claimed (design review 2026-11,
	// #3): the languages the footer's switcher offers — the advertised ones
	// plus the reader's own, the one rule the sitemap and hreflang use too —
	// each in its own script, right under the search. Same switch as the
	// footer: lang.choose(), so the choice outranks a synced profile locale.
	const languages = $derived(footerLocales(lang.available, lang.current));

	// The library's breadth as numbers (#6): this language's own counts from
	// the build's snapshot, in the share card's words. Hidden where the
	// snapshot came back empty (offline), rather than claiming "0 books".
	const countsLine = $derived(
		counts.books
			? t('home.shareCounts')
					.replace('{books}', counts.books.toLocaleString(lang.current))
					.replace('{sermons}', counts.sermons.toLocaleString(lang.current))
					.replace('{languages}', languages.length.toLocaleString(lang.current))
			: ''
	);

	// While this field is on screen the header's search pill hides (#5): two
	// search boxes 150px apart read as two different searches. "On screen"
	// starts below the sticky nav bar, which covers the field as it scrolls
	// away; and a hero the boot flag holds hidden (a signed-in reader's page
	// before the dashboard mounts, app.css) is not on screen at all.
	let form: HTMLFormElement;
	onMount(() => {
		const bar = document.querySelector('nav.appnav')?.getBoundingClientRect().height ?? 0;
		const io = new IntersectionObserver(
			([e]) =>
				(heroSearch.visible =
					e.isIntersecting && (form.checkVisibility?.({ visibilityProperty: true }) ?? true)),
			{ rootMargin: `-${Math.round(bar)}px 0px 0px 0px` }
		);
		io.observe(form);
		return () => {
			io.disconnect();
			heroSearch.visible = false;
		};
	});
</script>

<section class="page-col px-5 pt-8 sm:pt-16">
	<div class="intro">
		<div class="min-w-0">
			<h1 class="text-display mb-4 max-w-xl">{t('home.heroTitle')}</h1>
			<p class="mb-6 max-w-lg text-body text-muted">{t('home.heroTagline')}</p>
			<form
				bind:this={form}
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
			{#if languages.length > 1}
				<nav class="mb-6 flex max-w-lg flex-wrap items-center gap-2" aria-label={t('nav.language')}>
					{#each languages as l (l.code)}
						<a
							href={localeHome('/', { locale: l.code as (typeof locales)[number] })}
							class="lang-pill"
							aria-current={l.code === lang.current ? 'true' : undefined}
							lang={l.code}
							dir={getTextDirection(l.code)}
							onclick={(e) => {
								if (!isUnmodifiedPrimaryClick(e)) return;
								e.preventDefault();
								lang.choose(l.code);
							}}>{l.native_name}</a
						>
					{/each}
				</nav>
			{/if}
			<!-- The one primary on the view, named for where it goes (#4): the
			     library. Today's reading is the second way in — the Today card
			     just below, not /today, which a language with no devotionals
			     leaves empty (TodayCard drops its own link there for the same
			     reason). About lives in the footer, out of the reading path. -->
			<div class="flex flex-wrap items-center gap-x-6 gap-y-3">
				<a href={localizeHref('/books')} class="btn btn-primary btn-solid">{t('home.browseLibrary')}</a>
				<a href="#today" class="text-body font-semibold">{t('home.todayReading')} <Arrow /></a>
			</div>
			{#if countsLine}
				<p class="mt-5 text-body font-semibold text-text">{countsLine}</p>
			{/if}
			<p class="{countsLine ? 'mt-1' : 'mt-5'} text-small text-muted">
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
	/* A language, named in its own script: a pill, the current one marked in
	   accent. Tap targets reach 2rem without crowding the hero. */
	.lang-pill {
		display: inline-flex;
		align-items: center;
		min-height: 2rem;
		padding: 0.15rem 0.8rem;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-pill);
		background: var(--surface);
		color: var(--text);
		font-size: var(--fs-small);
		text-decoration: none;
	}
	.lang-pill:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
	.lang-pill[aria-current='true'] {
		border-color: var(--accent);
		color: var(--accent);
		font-weight: 600;
		box-shadow: inset 0 0 0 1px var(--accent);
	}
</style>
