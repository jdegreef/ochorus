<script lang="ts">
	import { onMount } from 'svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import BrandMark from '$lib/components/BrandMark.svelte';
	import { SITE_URL } from '$lib/config';
	import { dateKey } from '$lib/dailyDate';
	import { EMBED_HEIGHT_MESSAGE } from '$lib/embed';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { contentLang, readingTime } from '$lib/reading';
	import { watchToday } from '$lib/today';
	import { loadTodayPicks, type TodayPicks } from '$lib/todayPicks';

	/**
	 * "Today from Ochorus" — the church-website widget's card ($lib/embed): the
	 * day's verse, reading and sermon (the home page's Today card's picks,
	 * $lib/todayPicks), made to sit in a church site's sidebar or page. Drawn
	 * by /embed/today inside embed.js's iframe, and inline as the live preview
	 * on the /for/ pages (ForEmbed). Every link is a plain ochorus.com URL
	 * opening in a new tab, so a visitor who follows one keeps the church's
	 * page. Stacked in a narrow frame, three columns in a wide one. A language
	 * with no devotional or no sermon drops that part.
	 */
	let {
		report = false,
		onopen
	}: {
		/** Post the card's height to the parent window (embed.js sizes its
		 *  iframe by it): only when this is the framed page itself. */
		report?: boolean;
		/** Which link a visitor followed (the verse is not one). */
		onopen?: (part: 'brand' | 'reading' | 'sermon' | 'more') => void;
	} = $props();

	const t = i18n.t;

	let picks = $state<TodayPicks | null>(null);
	let dateLabel = $state('');
	let pickedFor = '';
	let card = $state<HTMLElement>();

	/** An absolute ochorus.com link: the widget lives on someone else's page. */
	const out = (path: string) => `${SITE_URL}${localizeHref(path)}`;

	async function loadToday(now: Date) {
		const key = dateKey(now);
		if (key === pickedFor) return;
		pickedFor = key;
		const lang = getLang();
		const next = await loadTodayPicks(now, lang);
		if (key !== pickedFor) return;
		dateLabel = now.toLocaleDateString(lang, { weekday: 'long', day: 'numeric', month: 'long' });
		picks = next;
	}

	onMount(() => watchToday((now) => void loadToday(now)));

	// Tell embed.js how tall the card is, so the iframe fits it with no inner
	// scrollbar — again whenever it changes (the picks land, a font swaps in,
	// the frame is resized). Only the height leaves this page.
	$effect(() => {
		if (!report || !card || window.parent === window) return;
		const send = () =>
			window.parent.postMessage({ type: EMBED_HEIGHT_MESSAGE, height: card!.getBoundingClientRect().height }, '*');
		const ro = new ResizeObserver(send);
		ro.observe(card);
		return () => ro.disconnect();
	});

	const columns = $derived(picks ? [picks.verse, picks.reading, picks.sermon].filter(Boolean).length : 3);
	// Static class names, so Tailwind sees each one.
	const GRID = ['', '', 'wide-2', 'wide-3'];
</script>

<article class="widget rounded-card border border-border bg-surface p-5" bind:this={card} aria-busy={!picks}>
	<header class="flex items-center justify-between gap-3">
		<a class="brand" href={out('/')}
		target="_blank"
		rel="noopener"
		aria-label="Ochorus"
		onclick={() => onopen?.('brand')}><BrandMark height={28} /></a>
		<p class="min-w-0 truncate text-small text-muted">
			<span class="eyebrow text-accent">{t('home.todayTitle')}</span>{#if dateLabel}{` · ${dateLabel}`}{/if}
		</p>
	</header>

	{#if picks}
		{#if columns}
			<ul role="list" class="parts m-0 mt-4 list-none p-0 {GRID[columns]}">
				{#if picks.verse}
					{@const v = picks.verse}
					<li class="part">
						<span class="eyebrow block text-accent">{t('home.todayVerse')}</span>
						<span class="title verse mt-2 block text-body" lang={v.lang} dir="auto">{v.text}</span>
						<span class="mt-2 block text-small text-muted" lang={v.lang} dir="auto">{v.ref}</span>
					</li>
				{/if}
				{#if picks.reading}
					{@const r = picks.reading}
					<li class="part">
						<a class="part-link" href={out(`/today/${r.book.slug}/`)}
							target="_blank"
							rel="noopener"
							onclick={() => onopen?.('reading')}>
							<span class="eyebrow block text-accent">{t('home.todayReading')}</span>
							<span class="title mt-2 block text-h3" lang={contentLang(r.book.language)} dir="auto"
								>{r.heading || r.book.title}</span
							>
							<span class="mt-1 block text-small text-muted" lang={contentLang(r.book.language)} dir="auto"
								>{r.heading ? `${r.book.title} · ${r.book.author.name}` : r.book.author.name}</span
							>
						</a>
					</li>
				{/if}
				{#if picks.sermon}
					{@const s = picks.sermon}
					<li class="part">
						<a class="part-link" href={out(`/sermons/${s.slug}`)}
							target="_blank"
							rel="noopener"
							onclick={() => onopen?.('sermon')}>
							<span class="eyebrow block text-accent">{t('home.sermonOfDay')}</span>
							<span class="title mt-2 block text-h3" dir="auto">{s.title}</span>
							<span class="mt-1 block text-small text-muted">{s.author.name} · {readingTime(s.word_count)}</span>
						</a>
					</li>
				{/if}
			</ul>
		{/if}
		<p class="mt-4 text-small font-semibold">
			<a class="text-accent hover:underline" href={out(picks.reading ? '/today/' : '/')}
				target="_blank"
				rel="noopener"
				onclick={() => onopen?.('more')}
				>{t('embed.readFree')} <Arrow /></a
			>
		</p>
	{:else}
		<!-- The card's shape while the day is picked. -->
		<div class="mt-4" aria-hidden="true">
			{#each [0, 1, 2] as i (i)}
				<div class="part">
					<div class="skeleton h-3 w-24 rounded"></div>
					<div class="skeleton mt-3 h-5 w-3/4 rounded"></div>
					<div class="skeleton mt-2 h-4 w-32 rounded"></div>
				</div>
			{/each}
		</div>
	{/if}
</article>

<style>
	/* Parts parted by a hairline: above each one after the first while they
	   stack, beside it once a wide frame lays them in a row (TodayCard's). */
	.part + .part {
		margin-block-start: 1rem;
		padding-block-start: 1rem;
		border-block-start: 1px solid var(--border);
	}
	@media (min-width: 40rem) {
		.wide-2,
		.wide-3 {
			display: grid;
		}
		.wide-2 {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.wide-3 {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
		.wide-2 .part + .part,
		.wide-3 .part + .part {
			margin-block-start: 0;
			padding-block-start: 0;
			border-block-start: 0;
			margin-inline-start: 1.25rem;
			padding-inline-start: 1.25rem;
			border-inline-start: 1px solid var(--border);
		}
	}
	.brand {
		color: var(--color-text);
		flex-shrink: 0;
	}
	.part-link {
		display: block;
		color: var(--color-text);
		text-decoration: none;
	}
	.title {
		font-family: var(--font-display);
		font-weight: 500;
		text-wrap: balance;
		transition: color var(--duration-fast);
	}
	/* Read, not scanned: body size, book weight, no italic (TodayCard's). */
	.verse {
		font-weight: 400;
	}
	.part-link:hover .title,
	.part-link:focus-visible .title {
		color: var(--color-accent);
	}
</style>
