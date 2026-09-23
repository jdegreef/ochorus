<script lang="ts">
	import type { CoverBook, TopicCount } from '$lib/library-public';
	import * as m from '$lib/paraglide/messages.js';
	import { auth } from '$lib/auth.svelte';
	import ContinueReading from '$lib/components/ContinueReading.svelte';
	import OnboardingCard from '$lib/components/OnboardingCard.svelte';
	import DashboardStats from '$lib/components/DashboardStats.svelte';
	import TodaysReading from '$lib/components/TodaysReading.svelte';
	import PlansProgress from '$lib/components/PlansProgress.svelte';
	import RecommendedNext from '$lib/components/RecommendedNext.svelte';
	import FavoritesShelf from '$lib/components/FavoritesShelf.svelte';
	import SermonOfTheWeek from '$lib/components/SermonOfTheWeek.svelte';
	import DiscoverStrip from '$lib/components/DiscoverStrip.svelte';
	import TopicChips from '$lib/components/TopicChips.svelte';

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

	// The display name if the reader set one, else the local part of their email
	// (never the full address — a greeting is not the place to print it). The
	// whole clause is dropped when we have neither, leaving a bare "Welcome back".
	const greetingName = $derived(auth.displayName || (auth.user?.email?.split('@')[0] ?? ''));
</script>

<section class="page-col px-5 pt-10 sm:pt-14">
	<!-- Parameterised so the name sits where each language wants it, rather than a
	     hardcoded ", {name}" — Paraglide's message function, not the param-free
	     t() facade. Falls back to a bare "Welcome back" when we have no name. -->
	<h1 class="text-h1">
		{greetingName ? m.home_welcome_back_named({ name: greetingName }) : m.home_welcome_back()}
	</h1>
</section>

<!-- Brand-new signed-in reader with nothing yet: a warm start, not empty blocks.
     Self-hides the moment there's any reading, favourite or plan. -->
<OnboardingCard />

<!-- Resume first: the one thing a returning reader most likely came back to do.
     Promoted above every other block, full width, with deep-link resume. -->
<ContinueReading />

<!-- Streak, weekly goal, reading calendar and totals — self-hides until there's
     activity to show (replaces the compact ReadingNudge on the dashboard). -->
<DashboardStats />

<!-- Today's plan day, then multi-plan progress -->
<TodaysReading />
<PlansProgress />

<!-- Personalised discovery — self-hides until there is history to score against -->
<RecommendedNext />

<!-- Saved items -->
<FavoritesShelf />

<!-- Generic discovery for a reader with little history yet (RecommendedNext
     above self-hides without one). Same six-book strip as the logged-out page. -->
<DiscoverStrip books={featured} />

<SermonOfTheWeek />

<!-- Browse by topic — the last block on the dashboard, so it carries the
     trailing bottom padding. -->
<TopicChips {topics} lastBlock />
