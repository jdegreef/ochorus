<script lang="ts">
	import { onMount } from 'svelte';
	import { dailyHighlight, type DailyHighlight } from '$lib/dailyHighlight';
	import { localDayNumber } from '$lib/dailyArticles';
	import { libraryBooks } from '$lib/resumeBooks';
	import { unslug } from '$lib/workTitles';
	import { workPath } from '$lib/editionHref';
	import { localizeHref } from '$lib/href';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { QUOTE_MAX } from '$lib/markAnchor';

	/**
	 * One of the reader's own highlights, met again on the dashboard — a
	 * different passage each day ($lib/dailyHighlight), as a card that opens
	 * the chapter it came from. Read from this device's marks on mount (the
	 * sign-in sync keeps them whole, and fires `ochorus:sync` when it lands),
	 * so it renders nothing until there is something to show. A book's title
	 * comes from the shared book list; anything else is named from its slug,
	 * like the notebook's own fallback.
	 */
	const t = i18n.t;
	let pick = $state<DailyHighlight | null>(null);
	let title = $state('');

	function load() {
		pick = dailyHighlight(localDayNumber(new Date()));
		if (!pick) return;
		const { kind, slug } = pick;
		title = unslug(slug);
		if (kind === 'book')
			libraryBooks(getLang())
				.then((books) => {
					const book = books.find((b) => b.slug === slug);
					if (book && pick?.slug === slug) title = book.title;
				})
				.catch(() => {});
	}

	onMount(() => {
		load();
		window.addEventListener('ochorus:sync', load);
		return () => window.removeEventListener('ochorus:sync', load);
	});

	// The stored quote is the passage's first QUOTE_MAX characters: say so
	// when it was cut.
	const text = $derived(pick ? (pick.text.length >= QUOTE_MAX ? `${pick.text}…` : pick.text) : '');
</script>

{#if pick}
	<section class="page-col px-5 pt-14">
		<a class="home-highlight" href={localizeHref(workPath(pick.kind, pick.slug, pick.order))}>
			<p class="eyebrow home-highlight-eyebrow">{t('notebook.fromReading')}</p>
			<blockquote class="home-highlight-text font-display">{text}</blockquote>
			{#if pick.note}
				<p class="home-highlight-note text-small">{pick.note}</p>
			{/if}
			<p class="mt-3 text-small text-muted">— {title}</p>
		</a>
	</section>
{/if}

<style>
	/* A highlighted passage as it looks on the page: the reader's gold wash
	   and a gilt rule down the start edge, on the card's ground. */
	.home-highlight {
		display: block;
		padding: 1.1rem 1.25rem 1.15rem;
		border: 1px solid var(--border);
		border-inline-start: 3px solid var(--gold);
		border-radius: var(--radius-card);
		background: color-mix(in srgb, var(--hl-gold) 9%, var(--surface));
		color: var(--text);
		text-decoration: none;
		transition:
			border-color var(--duration-fast),
			box-shadow var(--duration-fast);
	}
	.home-highlight:hover {
		border-color: var(--accent-soft-border);
		border-inline-start-color: var(--gold);
		box-shadow: var(--shadow-card);
		text-decoration: none;
	}
	.home-highlight-eyebrow {
		color: var(--muted);
		margin-bottom: 0.5rem;
	}
	.home-highlight-text {
		margin: 0;
		font-size: 1.15rem;
		line-height: 1.5;
		font-style: italic;
	}
	.home-highlight-note {
		margin-top: 0.6rem;
		color: var(--muted);
	}
</style>
