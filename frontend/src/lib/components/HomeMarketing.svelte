<script lang="ts">
	import type { BookSummary, AuthorBio, TopicSummary } from '$lib/library-public';
	import { goto } from '$app/navigation';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { portraitPosition } from '$lib/portraits';
	import ContinueReading from '$lib/components/ContinueReading.svelte';
	import ReadingNudge from '$lib/components/ReadingNudge.svelte';
	import SermonOfTheWeek from '$lib/components/SermonOfTheWeek.svelte';
	import DiscoverStrip from '$lib/components/DiscoverStrip.svelte';
	import TopicChips from '$lib/components/TopicChips.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';

	/**
	 * The logged-OUT home page: what a first-time visitor and every crawler sees.
	 * It is the prerendered, indexable surface — see the note in `+page.svelte` on
	 * why the baked HTML is always this component, never the dashboard.
	 *
	 * It stays acquisition-first (hero → discover → mission), but keeps the slim
	 * `ContinueReading` + `ReadingNudge` resume strip so a RETURNING reader who
	 * has not signed in still lands on their book rather than a fresh pitch. Both
	 * strip blocks render nothing without local reading activity, so a true first
	 * visit is unchanged. The heavier personal blocks (today's plan,
	 * recommendations, favourites) live only on the signed-in dashboard.
	 */
	interface HomeData {
		books: BookSummary[];
		featured: BookSummary[];
		authors: AuthorBio[];
		topics?: TopicSummary[];
	}
	let { data }: { data: HomeData } = $props();

	const featured = $derived<BookSummary[]>(data.featured);
	const authors = $derived<AuthorBio[]>(data.authors);
	const topics = $derived<TopicSummary[]>(data.topics ?? []);

	const t = i18n.t;

	// Hero search → the full search page. Progressive enhancement: the form is a
	// real GET to /search (works with no JS); with JS we intercept and navigate
	// client-side so it stays in the SPA.
	let query = $state('');
	function submitSearch(e: Event) {
		e.preventDefault();
		const q = query.trim();
		goto(localizeHref('/search') + (q ? `?q=${encodeURIComponent(q)}` : ''));
	}

	const initials = (name: string) =>
		name
			.split(' ')
			.filter(Boolean)
			.map((w) => w[0])
			.slice(0, 2)
			.join('')
			.toUpperCase();
</script>

<!-- Continue reading + streak render ABOVE the acquisition hero: a returning
     reader came back to resume, not to be sold the site again, and leaving
     these under a full-height hero meant scrolling past a pitch they had
     already accepted. Both render nothing until there is reading activity, so
     a first-time visitor still lands on the hero and sees no change.

     The reordering is `order`, not DOM order, so the page's only <h1> still
     comes before every <h2> in the source — a document that opens on an <h2>
     is a worse outline for anyone navigating by heading. Client-side only
     (this page is prerendered), so the blocks appear at hydration rather than
     in the baked HTML. -->
<div class="flex flex-col">
	<!-- Hero -->
	<section class="order-2 border-b border-border bg-surface-2">
		<div class="mx-auto max-w-4xl px-5 py-14 text-center sm:py-20">
			<p class="eyebrow mb-4 text-accent">
				{t('home.heroEyebrow')}
			</p>
			<h1 class="text-display mx-auto mb-5 max-w-3xl">
				{t('home.heroTitle')}
			</h1>
			<p class="mx-auto mb-6 max-w-xl text-body text-muted">
				{t('home.heroTagline')}
			</p>
			<form
				onsubmit={submitSearch}
				method="GET"
				action={localizeHref('/search')}
				role="search"
				class="mx-auto mb-6 flex max-w-lg items-center gap-2 rounded-full border border-border bg-surface px-2 py-1.5 shadow-sm focus-within:border-accent"
			>
				<svg
					class="ms-2 h-5 w-5 shrink-0 text-muted"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
				</svg>
				<input
					bind:value={query}
					name="q"
					type="search"
					enterkeyhint="search"
					placeholder={t('search.placeholder')}
					aria-label={t('nav.search')}
					class="min-w-0 flex-1 bg-transparent py-1 text-body text-text placeholder:text-muted focus-visible:-outline-offset-2"
				/>
				<button type="submit" class="btn btn-primary shrink-0 rounded-full">{t('nav.search')}</button>
			</form>
			<!-- One primary per view: the search submit above. These two are the
			     alternative routes into the same library, not competing calls to
			     action, so they read as secondary. -->
			<div class="flex flex-wrap justify-center gap-3">
				<a href={localizeHref('/books')} class="btn btn-ghost">{t('home.browseLibrary')}</a>
				<a href={localizeHref('/about')} class="btn btn-ghost">{t('home.aboutOchorus')}</a>
			</div>
		</div>
	</section>
	<div class="personal order-1"><ContinueReading books={data.books} /><ReadingNudge /></div>
</div>

<!-- Discover Your Next Book — above the plan/sermon blocks -->
<DiscoverStrip books={featured} />

<!-- Sermon of the week — editorial content discovery, not personal. Renders
     nothing when there is no featured sermon in the current language. -->
<SermonOfTheWeek />

<!-- Browse by topic -->
<TopicChips {topics} />

<!-- Mission teaser -->
<section class="mt-14 border-y border-border bg-surface-2">
	<div class="mx-auto max-w-3xl px-5 py-16 text-center">
		<h2 class="text-h1 mb-3">{t('home.missionTitle')}</h2>
		<p class="mx-auto max-w-xl text-body text-muted">
			{t('home.missionText')}
		</p>
		<a href={localizeHref('/about')} class="btn btn-ghost mt-6">{t('home.ourStory')}</a>
	</div>
</section>

<!-- Christian Authors — hidden when the shelf is empty, same reason as
     "Discover your next book" above. -->
{#if authors.length}
	<section class="page-col px-5 pt-14 pb-20">
		<SectionHeader
			title={t('home.authorsTitle')}
			href={localizeHref('/biographies')}
			linkText={t('home.allBiographies')}
		/>
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
			{#each authors as author (author.slug)}
				<a
					href={localizeHref(`/authors/${author.slug}`)}
					class="flex items-center gap-3 rounded-card border border-border p-4 hover:no-underline hover:bg-surface-2"
				>
					{#if author.photo_url}
						<img
							src={author.photo_url}
							alt="{t('a11y.portraitOf')} {author.name}"
							loading="lazy"
							class="h-11 w-11 shrink-0 rounded-full border border-border object-cover"
							style="filter: grayscale(1); object-position: {portraitPosition(author.slug)}"
						/>
					{:else}
						<span
							class="font-display flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent-soft text-small font-semibold text-accent"
						>
							{initials(author.name)}
						</span>
					{/if}
					<span>
						<span class="block text-small font-semibold text-text">{author.name}</span>
						<span class="block text-small text-muted">
							{author.book_count}
							{author.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
						</span>
					</span>
				</a>
			{/each}
		</div>
	</section>
{/if}

<style>
	/*
	 * The strip only exists for a returning reader: both blocks inside render
	 * nothing when there is no reading activity, leaving a wrapper whose only
	 * children are Svelte's anchor comments — which is `:empty` per the spec.
	 * So the closing rule and the space above the hero come and go with the
	 * content, and a first visit is exactly the page it was before.
	 */
	.personal:not(:empty) {
		padding-bottom: 3.5rem;
		border-bottom: 1px solid var(--border);
	}
</style>
