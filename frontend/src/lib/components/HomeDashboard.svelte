<script lang="ts">
	import type { CoverBook, TopicCount } from '$lib/library-public';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/auth.svelte';
	import { localizeHref } from '$lib/href';
	import { getLang } from '$lib/lang.svelte';
	import { hasStarted, readerActivity } from '$lib/readerActivity';
	import { welcome } from '$lib/welcome.svelte';
	import { currentBook } from '$lib/currentBook.svelte';
	import { greetingName } from '$lib/greeting';
	import ContinueReading from '$lib/components/ContinueReading.svelte';
	import OnboardingCard from '$lib/components/OnboardingCard.svelte';
	import WelcomeProgress from '$lib/components/WelcomeProgress.svelte';
	import WelcomePalette from '$lib/components/WelcomePalette.svelte';
	import DashboardStats from '$lib/components/DashboardStats.svelte';
	import TodaysReading from '$lib/components/TodaysReading.svelte';
	import PlansProgress from '$lib/components/PlansProgress.svelte';
	import RecommendedNext from '$lib/components/RecommendedNext.svelte';
	import FavoritesShelf from '$lib/components/FavoritesShelf.svelte';
	import SermonOfTheWeek from '$lib/components/SermonOfTheWeek.svelte';
	import HomeArticles from '$lib/components/HomeArticles.svelte';
	import DiscoverStrip from '$lib/components/DiscoverStrip.svelte';
	import TopicChips from '$lib/components/TopicChips.svelte';
	import HomeHero from '$lib/components/HomeHero.svelte';
	import HomeQuote from '$lib/components/HomeQuote.svelte';
	import HomeYear from '$lib/components/HomeYear.svelte';

	/**
	 * The signed-in home: a reading dashboard, not an acquisition page. Rendered
	 * only client-side, only for a signed-in user (see the branch in
	 * `+page.svelte`), so it never touches the prerendered HTML the crawlers get.
	 *
	 * Personal-first order: resume where they left off, then their streak, plan,
	 * recommendations and favourites — the marketing hero, mission and author
	 * roster stay on the logged-out page. Discovery still trails the personal
	 * blocks so a reader with no history yet has somewhere to start; each block
	 * self-hides when it has nothing to show.
	 */
	// The dashboard never shows the author roster (that lives on the marketing
	// page), so it takes a narrower slice of the page data than HomeMarketing.
	interface HomeData {
		featured: CoverBook[];
		topics?: TopicCount[];
	}
	let { data }: { data: HomeData } = $props();

	const featured = $derived<CoverBook[]>(data.featured);
	const topics = $derived<TopicCount[]>(data.topics ?? []);

	// The reader's first name (or their email's local part — never the full
	// address); HomeHero greets it for the time of their day.
	const name = $derived(greetingName(auth.displayName, auth.user?.email));

	// Every sign-up path (password, emailed code, Google) ends on this page, so
	// this is where a brand-new account is sent on to /welcome — once, and only
	// from home: a reader who signed up over a book stays on the book until they
	// next come home. `pagePending` is set by the fresh sign-in (auth) or read
	// back from storage here. A reader who has already started reading by then
	// has found their way in, so the welcome is settled without the detour.
	onMount(() => welcome.init());

	// The book the reader is in, decided once here for the hero (its resume
	// point) and the strip (which leaves it out). Resolved at creation from the
	// cache — this component renders client-side only — so the hero's first
	// paint is already theirs.
	currentBook.refresh();
	onMount(() => currentBook.watch());
	$effect(() => {
		if (!welcome.pagePending) return;
		if (hasStarted(readerActivity(getLang()))) welcome.pageSeen();
		else goto(localizeHref('/welcome'), { replaceState: true });
	});
</script>

<!-- The greeting over the painting of the book they're reading. -->
<HomeHero current={currentBook.item} {name} />

<!-- Just signed up: choose the colours of your library (once; see WelcomePalette).
     Held back while the /welcome page is still owed, so the card doesn't flash
     on the way there; it greets the reader on their next visit home instead. -->
{#if !welcome.pagePending}
	<WelcomePalette />
{/if}

<!-- Brand-new signed-in reader with nothing yet: a warm start, not empty blocks.
     Self-hides the moment there's any reading, favourite or plan. -->
<OnboardingCard />

<!-- Seen /welcome but not finished its checklist: keep the next step one tap
     away (self-hides when done, hidden, or while OnboardingCard is up). -->
<WelcomeProgress />

<!-- Resume first: the one thing a returning reader most likely came back to do.
     The current book is already the hero's resume point, so the strip carries
     the rest of what's in progress (and hides when that is nothing). -->
<ContinueReading exclude={currentBook.key} />

<!-- Streak, weekly goal, reading calendar and totals — self-hides until there's
     activity to show (replaces the compact ReadingNudge on the dashboard). On a
     parchment band, which collapses with it. -->
<div class="page-band">
	<DashboardStats />
	<!-- This year's finished covers, under the stats on the same parchment. -->
	<HomeYear />
</div>

<!-- Today's plan day beside multi-plan progress — side by side where both
     show and there is room, one full column when either hides (.dash-pair). -->
<div class="dash-pair page-col px-5">
	<TodaysReading />
	<PlansProgress />
</div>

<!-- Today's word: a line from the library over a painting (English only),
     beside the sermon of the week. -->
<div class="dash-pair page-col px-5">
	<HomeQuote />
	<SermonOfTheWeek />
</div>

<!-- Personalised discovery — self-hides until there is history to score against -->
<RecommendedNext />

<!-- Saved items -->
<FavoritesShelf />

<!-- Generic discovery for a reader with little history yet (RecommendedNext
     above self-hides without one). Same six-book strip as the logged-out page. -->
<DiscoverStrip books={featured} />

<!-- Eight articles for today — turns over daily; renders nothing in a language
     with fewer than eight articles. -->
<div class="page-band">
	<HomeArticles />
</div>

<!-- Browse by topic — the last block on the dashboard, so it carries the
     trailing bottom padding. -->
<TopicChips {topics} lastBlock />
