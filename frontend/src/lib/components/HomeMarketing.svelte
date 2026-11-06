<script lang="ts">
	import type { CoverBook, CoverFace, AuthorTileData, TopicCount, HubAudience } from '$lib/library-public';
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
	import Portrait from '$lib/components/Portrait.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import HomeForGroups from '$lib/components/HomeForGroups.svelte';
	import SignupBand from '$lib/components/SignupBand.svelte';
	import HomeIntro from '$lib/components/HomeIntro.svelte';

	/**
	 * The logged-OUT home page: what a first-time visitor and every crawler sees.
	 * It is the prerendered, indexable surface — see the note in `+page.svelte` on
	 * why the baked HTML is always this component, never the dashboard.
	 *
	 * It stays acquisition-first (hero → books → topics → authors), but keeps the
	 * slim `ContinueReading` + `ReadingNudge` resume strip so a RETURNING reader
	 * who has not signed in still lands on their book rather than a fresh pitch.
	 * Both strip blocks render nothing without local reading activity, so a true
	 * first visit is unchanged. The heavier personal blocks (today's plan,
	 * recommendations, favourites) live only on the signed-in dashboard.
	 *
	 * Design #17 ("Home in six sections"): one ground, sections parted by space
	 * alone — no tinted bands — and one heading style, a start-aligned
	 * sentence-case `<SectionHeader>` with no icon. "How Ochorus works" is gone;
	 * the library's figures and the mission paragraph live on /about.
	 */
	interface HomeData {
		hero?: CoverFace[];
		featured: CoverBook[];
		discover?: CoverBook[];
		authors: AuthorTileData[];
		topics?: TopicCount[];
		audiences?: HubAudience[];
	}
	let { data }: { data: HomeData } = $props();

	const featured = $derived<CoverBook[]>(data.discover ?? data.featured);
	const authors = $derived<AuthorTileData[]>(data.authors);
	const topics = $derived<TopicCount[]>(data.topics ?? []);

	const t = i18n.t;
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
     in the baked HTML.

     Design #10 (Continue reading for returning readers) builds on this strip:
     it takes the hero's place for a reader who has one. -->
<div class="flex flex-col">
	<!-- Hero: what the reader gets, beside a spread of the library's covers,
	     on the page's own ground (HomeIntro). -->
	<div class="order-2"><HomeIntro covers={data.hero ?? []} /></div>
	<!-- The strip's space before the app runs, for a reader app.html's boot
	     flag knows is returning: the rest of the page shows at once, below the
	     strip's frame, and the real strip takes the frame's place at mount
	     without moving it. After `.personal`, so CSS can drop the hold the
	     moment `.personal` fills (sibling selector, no :has). In the baked HTML
	     for everyone, shown to no one else (display: none). -->
	<div class="personal order-1"><ContinueReading /><ReadingNudge /></div>
	<div class="home-hold order-1">{@render continueHold()}{@render nudgeHold()}</div>
</div>

<!-- Design #20 (Today: verse · devotional · sermon) slots in HERE, between
     the hero and the books. Until it does, the day's blocks (DailyShelf,
     SermonOfTheDay, HomeArticles) keep their place below the book row. -->

<!-- Books -->
<DiscoverStrip books={featured} band="none" belowHero />

<!-- Create-an-account band. Four bands run behind one component (three A/B
     arms + a progress-targeted one); it self-gates on `auth.enabled`, so it
     stays hidden where accounts don't work and never bakes into the
     prerendered HTML. See SignupBand. -->
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

<!-- Topics: eight names; the header links to all of them. -->
<TopicChips {topics} quiet />

<!-- For young readers and teens — the hubs this language has. -->
<HomeAudienceHubs audiences={data.audiences ?? []} />

<!-- Authors: a row of faces with the name under each. Hidden when the shelf
     is empty, same reason as the book row. -->
{#if authors.length}
	<section class="page-col px-5 pt-14">
		<SectionHeader
			title={t('home.authorsTitle')}
			href={localizeHref('/biographies')}
			linkText={t('home.allBiographies')}
		/>
		<ul class="grid grid-cols-4 gap-x-3 gap-y-6 lg:grid-cols-8">
			{#each authors as author (author.slug)}
				<li>
					<a
						href={localizeHref(`/authors/${author.slug}`)}
						class="group flex flex-col items-center gap-2.5 text-center hover:no-underline"
					>
						<Portrait
							slug={author.slug}
							name={author.name}
							url={author.photo_url}
							px={96}
							tone="hover"
							decorative
							initialsClass="text-h3"
							class="aspect-square h-auto w-full max-w-[4.5rem] sm:max-w-24"
						/>
						<!-- Two lines at most. A phone's column can be ~70px (360px
						     screen) and the narrowest page width leaves ~80px at eight
						     a row, so the face shrinks to its cell (`w-full`, capped)
						     and a long single name ("Wigglesworth") breaks rather than
						     running into its neighbour. -->
						<span
							class="line-clamp-2 w-full break-words text-small font-medium text-text hyphens-auto group-hover:text-accent group-focus-visible:text-accent"
							>{author.name}</span
						>
					</a>
				</li>
			{/each}
		</ul>
	</section>
{/if}

<!-- The leader behind the reader: one closing line for churches and
     ministries and a link to the /for/ hub (design #27). -->
<div class="pb-20"><HomeForGroups /></div>

<style>
	/*
	 * The strip only exists for a returning reader: both blocks inside render
	 * nothing when there is no reading activity, leaving a wrapper whose only
	 * children are Svelte's anchor comments — which is `:empty` per the spec.
	 * So the closing rule and the space above the hero come and go with the
	 * content, and a first visit is exactly the page it was before.
	 */
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
