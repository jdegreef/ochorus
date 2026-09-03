<script lang="ts">
	import type { BookSummary, AuthorBio, TopicSummary } from '$lib/library-public';
	import { goto } from '$app/navigation';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { auth } from '$lib/auth.svelte';
	import ContinueReading from '$lib/components/ContinueReading.svelte';
	import ReadingNudge from '$lib/components/ReadingNudge.svelte';
	import SermonOfTheWeek from '$lib/components/SermonOfTheWeek.svelte';
	import DiscoverStrip from '$lib/components/DiscoverStrip.svelte';
	import TopicChips from '$lib/components/TopicChips.svelte';
	import AuthorTile from '$lib/components/AuthorTile.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
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
		books: BookSummary[];
		featured: BookSummary[];
		authors: AuthorBio[];
		topics?: TopicSummary[];
		counts?: { books: number; authors: number; sermons: number };
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

	// Library-breadth social proof under the hero: "N books · N authors · N
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
	<!-- Hero -->
	<section class="order-2 border-b border-border bg-surface-2">
		<div class="mx-auto max-w-4xl px-5 py-14 text-center sm:py-20">
			<p class="eyebrow mb-4 text-accent">
				{t('home.heroEyebrow')}
			</p>
			<h1 class="text-display mx-auto mb-5 max-w-3xl">
				{t('home.heroTitle')}
			</h1>
			<p class="mx-auto mb-4 max-w-xl text-body text-muted">
				{t('home.heroTagline')}
			</p>
			<!-- Library breadth, in the current language's own numbers -->
			{#if breadth.length}
				<p class="mb-6 text-small text-muted">
					{#each breadth as b, i (b.one)}{i > 0 ? ' · ' : ''}<span
							class="font-semibold text-text">{b.n}</span
						>
						{b.n === 1 ? t(b.one) : t(b.many)}{/each}
				</p>
			{/if}
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
			<!-- Trust row: the reasons to stay, at a glance -->
			<div class="mt-7 flex flex-wrap justify-center gap-x-6 gap-y-2">
				{#each proof as p (p.label)}
					<span class="inline-flex items-center gap-1.5 text-small text-muted">
						<span class="text-accent"><Icon name={p.icon} size={16} /></span>
						{p.label}
					</span>
				{/each}
			</div>
		</div>
	</section>
	<div class="personal order-1"><ContinueReading books={data.books} /><ReadingNudge /></div>
</div>

<!-- Discover Your Next Book — above the plan/sermon blocks -->
<DiscoverStrip books={featured} />

<!-- How it works — a first-time visitor's three steps, previewing the reading
     journey the dashboard delivers once they sign in. Static, so it shows on
     every logged-out visit. -->
<section class="page-col px-5 pt-14">
	<h2 class="text-h1 mb-8 text-center">{t('home.howTitle')}</h2>
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
     benefit — the natural moment to ask for the sign-up. The sync benefit is the
     reason to sign up, so lead with it. Only where accounts actually work (auth
     configured) — otherwise it would promise a feature the deployment lacks. -->
{#if auth.enabled}
	<section class="mt-14 border-y border-border bg-surface-2">
		<div class="mx-auto max-w-3xl px-5 py-16 text-center">
			<h2 class="text-h1 mb-3">{t('home.signupTitle')}</h2>
			<p class="mx-auto mb-6 max-w-xl text-body text-muted">{t('login.syncNote')}</p>
			<a href="{localizeHref('/login')}?mode=signup" class="btn btn-primary">
				{t('login.createAccountLink')}
			</a>
		</div>
	</section>
{/if}

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
	.personal:not(:empty) {
		padding-bottom: 3.5rem;
		border-bottom: 1px solid var(--border);
	}
</style>
