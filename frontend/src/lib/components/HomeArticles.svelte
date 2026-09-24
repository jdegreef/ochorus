<script lang="ts">
	import { onMount } from 'svelte';
	import { listArticles, type ArticleSummary } from '$lib/library-public';
	import { localDayNumber, pickDailyArticles } from '$lib/dailyArticles';
	import { getLang } from '$lib/lang.svelte';
	import { readingTime } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import SectionHeader from '$lib/components/SectionHeader.svelte';

	const t = i18n.t;

	/**
	 * "Eight for today" — a numbered two-column list of eight articles that
	 * turns over every day (see $lib/dailyArticles for the pick). Fetched
	 * CLIENT-SIDE, like SermonOfTheWeek: the home page is prerendered, and a
	 * build-time pick would freeze on the day of the last deploy.
	 *
	 * Articles are per-language rows with no English fallback, so the list is
	 * the reader's language's own shelf. The heading promises eight, so a
	 * language with fewer renders nothing (pickDailyArticles returns []).
	 */
	const COUNT = 8;

	let shelf: ArticleSummary[] = [];
	let picks = $state<ArticleSummary[]>([]);
	let dateLabel = $state('');
	let pickedDay = -1;

	// Re-picks only when the calendar day has moved, so a tab left open
	// overnight turns over when the reader comes back to it.
	function pickForToday() {
		const now = new Date();
		if (localDayNumber(now) === pickedDay) return;
		pickedDay = localDayNumber(now);
		picks = pickDailyArticles(shelf, now, COUNT);
		dateLabel = now.toLocaleDateString(getLang(), { weekday: 'long', day: 'numeric', month: 'long' });
	}

	onMount(() => {
		listArticles(getLang())
			.then((articles) => {
				shelf = articles;
				pickForToday();
			})
			.catch(() => {
				picks = [];
			});
		const onVisible = () => {
			if (document.visibilityState === 'visible' && shelf.length) pickForToday();
		};
		document.addEventListener('visibilitychange', onVisible);
		return () => document.removeEventListener('visibilitychange', onVisible);
	});

	// Two columns on wide screens, read down each: 1–4 on the left, 5–8 on the
	// right. On a phone the columns stack, so the numbers still run in order.
	const columns = $derived([picks.slice(0, COUNT / 2), picks.slice(COUNT / 2)]);
</script>

{#if picks.length}
	<section class="page-col px-5 pt-14">
		<div class="rounded-2xl border border-border bg-surface px-5 pb-3 pt-7 sm:px-10 sm:pt-9">
			<SectionHeader
				title={t('home.articlesTitle')}
				subtitle={`${dateLabel} · ${t('home.articlesSubtitle')}`}
				href={localizeHref('/articles/')}
				linkText={t('home.allArticles')}
			/>
			<div class="grid gap-x-14 md:grid-cols-2">
				{#each columns as column, c (c)}
					<!-- role="list": WebKit drops list semantics from list-style:none lists,
					     and the visible numerals are aria-hidden. -->
					<ol role="list" class="m-0 list-none p-0" start={c * (COUNT / 2) + 1}>
						{#each column as article, i (article.slug)}
							<li class="border-t border-border">
								<a class="daily-row" href={localizeHref(`/articles/${article.slug}/`)}>
									<span class="num" aria-hidden="true">{String(c * (COUNT / 2) + i + 1).padStart(2, '0')}</span>
									<span class="min-w-0">
										<span class="title block text-h3">{article.h1}</span>
										{#if article.description}
											<span class="mt-1 line-clamp-2 text-small text-muted">{article.description}</span>
										{/if}
										<span class="mt-2 block text-small text-muted">
											{#if article.topics?.[0]}<span class="font-semibold text-accent">{article.topics[0].title}</span>{` · `}{/if}{readingTime(article.word_count)}
										</span>
									</span>
								</a>
							</li>
						{/each}
					</ol>
				{/each}
			</div>
		</div>
	</section>
{/if}

<style>
	/* A numbered row, not a card: no border or ground of its own (the hairline
	   is on the <li>), so it hovers by turning the title to accent — the list's
	   one colour move, on hover and keyboard focus alike. */
	.daily-row {
		display: grid;
		grid-template-columns: 3.25rem minmax(0, 1fr);
		gap: 0.25rem;
		padding-block: 1.25rem;
		color: var(--color-text);
		text-decoration: none;
	}
	.num {
		font-family: var(--font-display);
		font-size: var(--fs-h1);
		font-weight: 300;
		line-height: 1;
		color: var(--color-gold);
		font-variant-numeric: lining-nums tabular-nums;
	}
	.title {
		font-family: var(--font-display);
		font-weight: 500;
		color: var(--color-text);
		text-wrap: balance;
		transition: color var(--duration-fast);
	}
	.daily-row:hover .title,
	.daily-row:focus-visible .title {
		color: var(--color-accent);
	}
</style>
