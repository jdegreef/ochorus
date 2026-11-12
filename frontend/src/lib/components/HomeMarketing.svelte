<script lang="ts">
	import { authorPath } from '$lib/originals';
	import type { CoverBook, CoverFace, AuthorTileData, TopicCount, HubAudience } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import ContinueReading, { hold as continueHold } from '$lib/components/ContinueReading.svelte';
	import ReadingNudge, { hold as nudgeHold } from '$lib/components/ReadingNudge.svelte';
	import TodayCard from '$lib/components/TodayCard.svelte';
	import TonightShelf from '$lib/components/TonightShelf.svelte';
	import type { TonightItem } from '$lib/tonightShelf';
	import DiscoverStrip from '$lib/components/DiscoverStrip.svelte';
	import TopicChips from '$lib/components/TopicChips.svelte';
	import NeedFinder from '$lib/components/NeedFinder.svelte';
	import { shownNeeds } from '$lib/needFinder';
	import HomeAudienceHubs from '$lib/components/HomeAudienceHubs.svelte';
	import Portrait from '$lib/components/Portrait.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import HomeForGroups from '$lib/components/HomeForGroups.svelte';
	import SignupBand from '$lib/components/SignupBand.svelte';
	import HomeIntro from '$lib/components/HomeIntro.svelte';
	import HomeResume, { hold as resumeHold } from '$lib/components/HomeResume.svelte';
	import { currentBook } from '$lib/currentBook.svelte';
	import { onMount } from 'svelte';

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
		/** Absent from a snapshot built before the shelf existed. */
		tonight?: TonightItem[];
		needs?: string[];
		/** This language's library counts, for the hero's numbers line. */
		counts?: { books: number; sermons: number };
	}
	let { data }: { data: HomeData } = $props();

	const featured = $derived<CoverBook[]>(data.discover ?? data.featured);
	const authors = $derived<AuthorTileData[]>(data.authors);
	const topics = $derived<TopicCount[]>(data.topics ?? []);
	// Gated as NeedFinder gates them, so one of the two always draws.
	const needs = $derived(shownNeeds(data.needs ?? []).map((n) => n.id));

	const t = i18n.t;

	// Design #10: a reader with a book open on this device gets "Continue
	// reading" in the hero's place. Decided at mount, from this device's
	// progress — the prerendered page (and hydration) is the newcomer's, and
	// app.html's boot flag hides its hero until then (see the style below).
	// `currentBook` is the store the signed-in hero uses: it knows WHICH book
	// at once and resolves the book itself from the cache or the list. A book
	// it cannot draw once the list has settled (the list failed: offline, the
	// API down) leaves the hero, not a skeleton, in place. `mounted` as well
	// as the key: the store is shared with the dashboard, so before this
	// page's refresh it may still hold another visit's book.
	let mounted = $state(false);
	onMount(() => {
		currentBook.refresh();
		mounted = true;
		return currentBook.watch();
	});
	const resuming = $derived(
		mounted && !!currentBook.key && (!!currentBook.item || currentBook.pending)
	);
</script>

<!-- Continue reading + streak render ABOVE the acquisition hero: a returning
     reader came back to resume, not to be sold the site again, and leaving
     these under a full-height hero meant scrolling past a pitch they had
     already accepted. Both render nothing until there is reading activity, so
     a first-time visitor still lands on the hero and sees no change.

     Design #10: a reader with a BOOK in progress here does not get the hero
     at all — HomeResume takes its place (the book, its chapter and one
     Resume button; a started plan's day beside it), and the strip under it
     carries the rest of what is in progress, leaving that book out.

     The reordering is `order`, not DOM order, so the page's only <h1> still
     comes before every <h2> in the source — a document that opens on an <h2>
     is a worse outline for anyone navigating by heading. Client-side only
     (this page is prerendered), so the blocks appear at hydration rather than
     in the baked HTML. -->
<div class="flex flex-col">
	<!-- "Continue reading" in the hero's place, and its frame before the app
	     runs: in the baked HTML for everyone, shown only where app.html's boot
	     flag saw a book in progress (`data-home-resume`), until the block
	     fills `.resume` (sibling selector, as `.home-hold` below). Nothing but
	     the block inside `.resume`: whitespace would make it never `:empty`. -->
	<div class="resume">{#if resuming}<HomeResume />{/if}</div>
	<div class="resume-hold">{@render resumeHold()}</div>
	<!-- Hero: what the reader gets, beside a spread of the library's covers,
	     on the page's own ground (HomeIntro). Hidden by the boot flag before
	     mount for a reader the block replaces it for. -->
	{#if !resuming}<div class="intro order-2"><HomeIntro covers={data.hero ?? []} counts={data.counts} /></div>{/if}
	<!-- The strip's space before the app runs, for a reader app.html's boot
	     flag knows is returning: the rest of the page shows at once, below the
	     strip's frame, and the real strip takes the frame's place at mount
	     without moving it. After `.personal`, so CSS can drop the hold the
	     moment `.personal` fills (sibling selector, no :has). In the baked HTML
	     for everyone, shown to no one else (display: none). -->
	<div class="personal order-1"><ContinueReading exclude={resuming ? currentBook.key : undefined} /><ReadingNudge /></div>
	<div class="home-hold order-1">{@render continueHold()}{@render nudgeHold()}</div>
</div>

<!-- Today (design #20): the day's verse, devotional reading and sermon in
     one card, between the hero and the books. It replaced the three day's
     blocks that sat below the book row (DailyShelf, SermonOfTheDay,
     HomeArticles); the signed-in dashboard keeps those. Client-side — its
     skeleton holds the card's place in the baked HTML. -->
<TodayCard />

<!-- Books -->
<DiscoverStrip books={featured} band="none" belowHero />

<!-- Tonight, under 20 minutes (idea #27): whole works to finish in one
     sitting, in the evening only. It appears at mount (the clock is the
     reader's), so it sits under the book row — below the first screen on
     every width — where its arrival moves nothing the reader is looking at;
     above the row it would push the books down after first paint. -->
<TonightShelf items={data.tonight ?? []} />

<!-- Create-an-account band. Four bands run behind one component (three A/B
     arms + a progress-targeted one); it self-gates on `auth.enabled`, so it
     stays hidden where accounts don't work and never bakes into the
     prerendered HTML. See SignupBand. -->
<SignupBand />

<!-- Topics, by situation: "What do you need today?" — chips that open three
     picks from a topic shelf, its header linking to all of them. It takes the
     topic row's slot rather than adding a section (design #17 trimmed the page
     on purpose): both are the page's one way into /topics, and a visitor from
     a search arrives with a need more often than a subject. A language whose
     shelves answer fewer than three situations keeps the eight topic names. -->
{#if needs.length}
	<NeedFinder {needs} />
{:else}
	<TopicChips {topics} quiet />
{/if}

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
						href={localizeHref(authorPath(author.slug))}
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
	/* Design #10's swap, before the app runs: the hero hidden and the block's
	   frame in its place, for a reader the boot flag saw a book open for. */
	.resume-hold {
		display: none;
	}
	/* If the app never says it is ready (a script error, a chunk that will
	   not load), the hero comes back after 3 s, as the member's page is
	   revealed (app.css home-reveal), instead of staying a skeleton. */
	:global(html[data-home-resume]:not([data-home-ready])) .resume:empty + .resume-hold {
		display: block;
		animation: resume-hold-end 0s 3s forwards;
	}
	/* Folded rather than display: none — an element that is display: none runs
	   no animation, so it could not come back on its own. */
	:global(html[data-home-resume]:not([data-home-ready])) .intro {
		height: 0;
		overflow: hidden;
		visibility: hidden;
		animation: resume-intro-back 0s 3s forwards;
	}
	@keyframes resume-hold-end {
		to {
			display: none;
		}
	}
	@keyframes resume-intro-back {
		to {
			height: auto;
			overflow: visible;
			visibility: visible;
		}
	}
</style>
