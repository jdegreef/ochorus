<script lang="ts">
	import type { CoverBook, AuthorTileData, TopicCount, HubAudience } from '$lib/library-public';
	import { goto } from '$app/navigation';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import ContinueReading, { hold as continueHold } from '$lib/components/ContinueReading.svelte';
	import ReadingNudge, { hold as nudgeHold } from '$lib/components/ReadingNudge.svelte';
	import DailyShelf from '$lib/components/DailyShelf.svelte';
	import SermonOfTheDay from '$lib/components/SermonOfTheDay.svelte';
	import HomeArticles from '$lib/components/HomeArticles.svelte';
	import DiscoverStrip from '$lib/components/DiscoverStrip.svelte';
	import TopicChips from '$lib/components/TopicChips.svelte';
	import HomeAudienceHubs from '$lib/components/HomeAudienceHubs.svelte';
	import AuthorTile from '$lib/components/AuthorTile.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import HomeForGroups from '$lib/components/HomeForGroups.svelte';
	import SignupBand from '$lib/components/SignupBand.svelte';
	import Icon, { type IconName } from '$lib/components/Icon.svelte';

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
		featured: CoverBook[];
		authors: AuthorTileData[];
		topics?: TopicCount[];
		counts?: { books: number; authors: number; sermons: number };
		audiences?: HubAudience[];
	}
	let { data }: { data: HomeData } = $props();

	const featured = $derived<CoverBook[]>(data.featured);
	const authors = $derived<AuthorTileData[]>(data.authors);
	const topics = $derived<TopicCount[]>(data.topics ?? []);

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

	// Library-breadth social proof in the mission band: "N books · N authors · N
	// sermons". Each figure drops out when the current language has none of that
	// kind, so a smaller locale never shows "0 sermons".
	const breadth = $derived(
		[
			{ n: data.counts?.books ?? 0, one: 'common.bookOne', many: 'common.bookMany' },
			{ n: data.counts?.authors ?? 0, one: 'common.authorOne', many: 'common.authorMany' },
			{ n: data.counts?.sermons ?? 0, one: 'common.sermonOne', many: 'common.sermonMany' }
		].filter((x) => x.n > 0)
	);

	// The trust row beneath the hero's calls to action.
	const proof: { icon: IconName; label: string }[] = [
		{ icon: 'heart', label: t('home.proofFree') },
		{ icon: 'wind', label: t('home.proofNoAds') },
		{ icon: 'headphones', label: t('home.proofOffline') }
	];

	// The three steps of the "how it works" row.
	const steps: { icon: IconName; title: string; text: string }[] = [
		{ icon: 'compass', title: t('home.howDiscoverTitle'), text: t('home.howDiscoverText') },
		{ icon: 'book', title: t('home.howReadTitle'), text: t('home.howReadText') },
		{ icon: 'flame', title: t('home.howTrackTitle'), text: t('home.howTrackText') }
	];
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
	<!-- Hero: plain words on the page's own ground — no painting, scrim or
	     grain — so the first screen reads light and calm, with the theme's ink
	     and its one accent (the search button). -->
	<section class="order-2">
		<div class="mx-auto max-w-4xl px-5 pt-14 text-center sm:pt-20">
			<p class="eyebrow mb-4 text-muted">
				{t('home.heroEyebrow')}
			</p>
			<h1 class="text-display mx-auto mb-5 max-w-3xl">
				{t('home.heroTitle')}
			</h1>
			<p class="mx-auto mb-7 max-w-xl text-body text-muted">
				{t('home.heroTagline')}
			</p>
			<form
				onsubmit={submitSearch}
				method="GET"
				action={localizeHref('/search')}
				role="search"
				class="mx-auto mb-6 flex max-w-lg items-center gap-2 rounded-full border border-border bg-surface px-2 py-1.5 shadow-sm focus-within:border-accent max-sm:gap-1"
			>
				<!-- On a phone the glass moves into the submit button, so the hint
				     ("Search books, authors, text…") has the width to be read whole
				     rather than cut at "tex". -->
				<svg
					class="ms-2 h-5 w-5 shrink-0 text-muted max-sm:hidden"
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
					class="min-w-0 flex-1 bg-transparent py-1 text-body text-text placeholder:text-muted focus-visible:-outline-offset-2 max-sm:ps-3 max-sm:placeholder:text-small"
				/>
				<button type="submit" class="btn btn-primary shrink-0 rounded-full max-sm:px-3">
					<Icon name="search" size={18} class="sm:hidden" />
					<span class="max-sm:sr-only">{t('nav.search')}</span>
				</button>
			</form>
			<!-- One primary per view: the search submit above. These two are the
			     alternative routes into the same library, not competing calls to
			     action, so they read as secondary. -->
			<div class="flex flex-wrap justify-center gap-3">
				<a href={localizeHref('/books')} class="btn btn-ghost">{t('home.browseLibrary')}</a>
				<a href={localizeHref('/about')} class="btn btn-ghost">{t('home.aboutOchorus')}</a>
			</div>
			<!-- Trust row: the reasons to stay, at a glance -->
			<div class="mt-7 flex flex-wrap justify-center gap-x-6 gap-y-2">
				{#each proof as p (p.label)}
					<span class="inline-flex items-center gap-1.5 text-small text-muted">
						<Icon name={p.icon} size={16} />
						{p.label}
					</span>
				{/each}
			</div>
		</div>
	</section>
	<!-- The strip's space before the app runs, for a reader app.html's boot
	     flag knows is returning: the rest of the page shows at once, below the
	     strip's frame, and the real strip takes the frame's place at mount
	     without moving it. After `.personal`, so CSS can drop the hold the
	     moment `.personal` fills (sibling selector, no :has). In the baked HTML
	     for everyone, shown to no one else (display: none). -->
	<div class="personal order-1"><ContinueReading /><ReadingNudge /></div>
	<div class="home-hold order-1">{@render continueHold()}{@render nudgeHold()}</div>
</div>

<!-- Discover Your Next Book — above the plan/sermon blocks -->
<DiscoverStrip books={featured} band="page" />

<!-- How it works — a first-time visitor's three steps, previewing the reading
     journey the dashboard delivers once they sign in. Static, so it shows on
     every logged-out visit. -->
<section class="page-col px-5 pt-14">
	<h2 class="text-h2 mb-8 text-center">{t('home.howTitle')}</h2>
	<div class="grid gap-8 sm:grid-cols-3">
		{#each steps as step (step.title)}
			<div class="text-center">
				<span
					class="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent"
				>
					<Icon name={step.icon} size={22} />
				</span>
				<h3 class="text-h3 mb-1.5">{step.title}</h3>
				<p class="mx-auto max-w-xs text-small text-muted">{step.text}</p>
			</div>
		{/each}
	</div>
</section>

<!-- Create-an-account band: right after "how it works" explains the tracking
     benefit — the natural moment to ask for the sign-up. Four bands run behind
     one component (three A/B arms + a progress-targeted one); it self-gates on
     `auth.enabled`, so it stays hidden where accounts don't work and never bakes
     into the prerendered HTML. See SignupBand. -->
<SignupBand />

<!-- Today in the devotionals — each year-long devotional's entry for the
     reader's date. Client-side; renders nothing in a language with none. -->
<DailyShelf />

<!-- Sermon of the day — editorial content discovery, not personal. Renders
     nothing when there is no featured sermon in the current language. -->
<SermonOfTheDay />

<!-- Eight articles for today — turns over daily; renders nothing in a language
     with fewer than eight articles. -->
<HomeArticles />

<!-- Browse by topic -->
<TopicChips {topics} />

<!-- For young readers and teens — the hubs this language has. -->
<HomeAudienceHubs audiences={data.audiences ?? []} />

<!-- The leader behind the reader: a page for each group they lead. -->
<HomeForGroups />

<!-- Mission teaser -->
<section class="mt-14 border-y border-border bg-surface-2">
	<div class="mx-auto max-w-3xl px-5 py-16 text-center">
		<!-- The library's breadth, in this language's own numbers, as the band's
		     figures: what the mission has put on the shelf so far. -->
		{#if breadth.length}
			<div class="mkt-numbers mb-10">
				{#each breadth as b (b.one)}
					<div>
						<div class="mkt-number font-display">{b.n}</div>
						<div class="eyebrow text-muted">{b.n === 1 ? t(b.one) : t(b.many)}</div>
					</div>
				{/each}
			</div>
		{/if}
		<h2 class="text-h2 mb-3">{t('home.missionTitle')}</h2>
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
			section="biographies"
			title={t('home.authorsTitle')}
			href={localizeHref('/biographies')}
			linkText={t('home.allBiographies')}
		/>
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
			{#each authors as author (author.slug)}
				<AuthorTile {author} />
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
	/* The mission band's figures: big serif numerals over small labels. */
	.mkt-numbers {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 1.5rem 3.5rem;
	}
	.mkt-number {
		font-size: var(--fs-h1);
		font-weight: 600;
		line-height: 1.1;
		color: var(--accent);
	}
	.personal:not(:empty),
	.home-hold {
		padding-bottom: 3.5rem;
		border-bottom: 1px solid var(--border);
	}
	/* The boot flag only names a returning reader when the strip will draw
	   something, so the hold is the strip's whole box, rule and all. */
	.home-hold {
		display: none;
	}
	/* Gone in the same frame the strip draws (`.personal` no longer empty),
	   not a frame later at `data-home-ready`, or that frame shows both. */
	:global(html[data-home-for='reader']:not([data-home-ready])) .personal:empty + .home-hold {
		display: block;
	}
</style>
