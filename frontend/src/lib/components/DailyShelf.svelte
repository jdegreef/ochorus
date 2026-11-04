<script lang="ts">
	import { onMount } from 'svelte';
	import { getDailyShelf, type DailyEntry } from '$lib/library-public';
	import { dateKey } from '$lib/dailyDate';
	import { getLang } from '$lib/lang.svelte';
	import { contentLang } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import BookCover from '$lib/components/BookCover.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';

	const t = i18n.t;

	/**
	 * "Today in the devotionals" — today's entry from each year-long devotional
	 * this language publishes (Days of Heaven upon Earth, Morning by Morning…),
	 * one card each, linking to that book's day page (/today/<slug>/). Fetched
	 * CLIENT-SIDE with the reader's own local date, like SermonOfTheDay: the
	 * home page is prerendered, and a build-time pick would freeze on the day
	 * of the last deploy. Renders nothing in a language with no dated books.
	 *
	 * `embedded` drops the section chrome and heading, for the /today page,
	 * which heads itself.
	 */
	let { embedded = false }: { embedded?: boolean } = $props();

	let readings = $state<DailyEntry[]>([]);
	// What the embedded page says instead of an empty column: null until the
	// first answer, then whether it failed.
	let failed = $state<boolean | null>(null);
	let dateLabel = $state('');
	let pickedFor = '';

	// Re-fetches only when the calendar day has moved, so a tab left open
	// overnight turns over when the reader comes back to it.
	function loadToday() {
		const now = new Date();
		const key = dateKey(now);
		if (key === pickedFor) return;
		pickedFor = key;
		dateLabel = now.toLocaleDateString(getLang(), { weekday: 'long', day: 'numeric', month: 'long' });
		getDailyShelf(key, getLang())
			.then((r) => {
				readings = r.readings;
				failed = false;
			})
			.catch(() => {
				readings = [];
				failed = true;
			});
	}

	onMount(() => {
		loadToday();
		const onVisible = () => {
			if (document.visibilityState === 'visible') loadToday();
		};
		document.addEventListener('visibilitychange', onVisible);
		return () => document.removeEventListener('visibilitychange', onVisible);
	});
</script>

{#snippet cards()}
	<ul role="list" class="m-0 grid list-none gap-4 p-0 sm:grid-cols-2">
		{#each readings as r (r.book.slug)}
			<li>
				<a
					class="daily-card card-tint rounded-card border border-border bg-surface"
					href={localizeHref(`/today/${r.book.slug}/`)}
					lang={contentLang(r.book.language)}
				>
					<!-- Decorative: the card names the book in words. -->
					<span class="w-14 shrink-0" aria-hidden="true"><BookCover book={r.book} rounded="rounded-sm" /></span>
					<span class="min-w-0">
						<span class="eyebrow block truncate text-accent" dir="auto">{r.book.title}</span>
						<!-- The day's own title where the book gives one, else its verse:
						     the date is the shelf's, so a card never repeats it. -->
						<span class="title mt-1 line-clamp-3 text-h3" dir="auto">{r.heading || r.excerpt || r.label}</span>
						{#if r.heading && r.excerpt}
							<span class="mt-1 line-clamp-3 text-small text-muted" dir="auto">{r.excerpt}</span>
						{/if}
						<span class="mt-2 block text-small text-muted">{r.book.author.name}</span>
					</span>
				</a>
			</li>
		{/each}
	</ul>
{/snippet}

{#if embedded && !readings.length && failed !== null}
	<p class="text-muted">{failed ? t('common.loadError') : t('daily.none')}</p>
{:else if readings.length}
	{#if embedded}
		{@render cards()}
	{:else}
		<section class="page-col px-5 pt-14">
			<SectionHeader
				title={t('daily.title')}
				subtitle={`${dateLabel} · ${t('daily.subtitle')}`}
				href={localizeHref('/today/')}
				linkText={t('daily.seeAll')}
			/>
			{@render cards()}
		</section>
	{/if}
{/if}

<style>
	/* A row card (border-tint hover, no lift — page-design D3), the shape of
	   ArticleCard: a small cover beside the day's words. */
	.daily-card {
		display: flex;
		gap: 1rem;
		height: 100%;
		padding: 1rem;
		color: var(--color-text);
		text-decoration: none;
	}
	.title {
		font-family: var(--font-display);
		font-weight: 500;
		text-wrap: balance;
		transition: color var(--duration-fast);
	}
	.daily-card:hover .title,
	.daily-card:focus-visible .title {
		color: var(--color-accent);
	}
</style>
