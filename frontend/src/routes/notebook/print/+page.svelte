<script lang="ts">
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import { localizeHref } from '$lib/href';
	import {
		daysWaited,
		journalForPrint,
		periodStart,
		type JournalEntry,
		type PrintPeriod
	} from '$lib/journal';
	import { journal } from '$lib/journal.svelte';

	/**
	 * The printable prayer journal: the Notebook set as a small book — a title
	 * page, then the answered prayers month by month, the prayers still being
	 * prayed (by person, with their updates), notes and daily prayers — for
	 * paper or "Save as PDF". The screen shows the options and a preview; the
	 * options never print (see the print rules below and app.css).
	 */
	const t = i18n.t;
	const locale = getLang();

	let period = $state<PrintPeriod>('year');
	let showAnswered = $state(true);
	let showPraying = $state(true);
	let showNotes = $state(true);
	let showDaily = $state(true);

	const now = new Date();
	const from = $derived(periodStart(period, now));
	const book = $derived(journalForPrint(journal.store, from));
	const prayingCount = $derived(book.praying.reduce((n, c) => n + c.prayers.length, 0));
	const empty = $derived(
		!(showAnswered && book.answeredCount) &&
			!(showPraying && prayingCount) &&
			!(showNotes && book.notes.length) &&
			!(showDaily && book.daily.length)
	);

	const date = (at: number) =>
		new Date(at).toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
	const monthName = (at: number) => new Date(at).toLocaleDateString(locale, { month: 'long', year: 'numeric' });
	const range = $derived(from ? `${date(from)} – ${date(now.getTime())}` : `${t('notebook.printUntil')} ${date(now.getTime())}`);

	function waited(p: JournalEntry): string {
		const n = daysWaited(p) ?? 0;
		if (n === 0) return t('notebook.answeredSameDay');
		if (n === 1) return t('notebook.answeredAfterOneDay');
		return m.notebook_answered_after_days({ n: String(n) });
	}

	const PERIODS: PrintPeriod[] = ['year', 'last12', 'month', 'all'];
</script>

<svelte:head><title>{t('notebook.printTitle')} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="page-col px-5 py-10">
	<!-- On screen only: what to print. -->
	<div class="controls">
		<a class="back text-small" href={localizeHref('/notebook')}>← {t('notebook.title')}</a>
		<h1 class="text-h1 mt-2">{t('notebook.printTitle')}</h1>
		<p class="mt-1 text-body text-muted">{t('notebook.printIntro')}</p>

		<div class="mt-5 flex flex-wrap items-center gap-2" role="group" aria-label={t('notebook.printPeriod')}>
			{#each PERIODS as p (p)}
				<button class="chip" class:active={period === p} aria-pressed={period === p} onclick={() => (period = p)}>
					{t(`notebook.printPeriod_${p}`)}
				</button>
			{/each}
		</div>
		<fieldset class="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-small">
			<legend class="sr-only">{t('notebook.printInclude')}</legend>
			<label><input type="checkbox" bind:checked={showAnswered} /> {t('notebook.tabAnswered')} ({book.answeredCount})</label>
			<label><input type="checkbox" bind:checked={showPraying} /> {t('notebook.statPraying')} ({prayingCount})</label>
			<label><input type="checkbox" bind:checked={showNotes} /> {t('settings.statNotes')} ({book.notes.length})</label>
			<label><input type="checkbox" bind:checked={showDaily} /> {t('notebook.dailyKind')} ({book.daily.length})</label>
		</fieldset>
		<div class="mt-5 flex flex-wrap items-center gap-3">
			<button class="btn btn-primary" onclick={() => window.print()} disabled={empty}><span aria-hidden="true" class="me-1">🖨</span>{t('notebook.printButton')}</button>
			<span class="text-micro text-muted">{t('notebook.printHint')}</span>
		</div>
	</div>

	{#if empty}
		<p class="empty">{t('notebook.printEmpty')}</p>
	{:else}
		<!-- The book itself: previewed as pages on screen, printed as paper. -->
		<article class="book" lang={locale}>
			<section class="title-page">
				<p class="kicker">Ochorus</p>
				<h2 class="book-title">{t('notebook.printTitle')}</h2>
				<p class="range">{range}</p>
				<p class="totals">
					{#if showAnswered && book.answeredCount}<span>{t('notebook.tabAnswered')}: {book.answeredCount}</span>{/if}
					{#if showPraying && prayingCount}<span>{t('notebook.statPraying')}: {prayingCount}</span>{/if}
					{#if showNotes && book.notes.length}<span>{t('settings.statNotes')}: {book.notes.length}</span>{/if}
				</p>
				<p class="epigraph">{t('notebook.printEpigraph')}</p>
			</section>

			{#if showAnswered && book.answeredCount}
				<section class="part">
					<h2 class="part-title">{t('notebook.tabAnswered')}</h2>
					{#each book.answered as mo (mo.month)}
						<h3 class="month">{monthName(mo.at)}</h3>
						{#each mo.prayers as p (p.id)}
							<div class="item">
								<p class="meta">
									{date(p.answeredAt!)}{#if p.person}{` · ${t('notebook.prayingFor')} ${p.person}`}{/if}
								</p>
								{#if p.title}<p class="item-title">{p.title}</p>{/if}
								{#if p.body}<p class="body">{p.body}</p>{/if}
								{#if p.answer}<p class="answer">✓ {p.answer}</p>{/if}
								<p class="meta">{t('notebook.printAsked')} {date(p.createdAt)} · {waited(p)}</p>
							</div>
						{/each}
					{/each}
				</section>
			{/if}

			{#if showPraying && prayingCount}
				<section class="part">
					<h2 class="part-title">{t('notebook.statPraying')}</h2>
					{#each book.praying as c (c.person.toLowerCase())}
						<h3 class="month">{c.person || t('notebook.forAnyone')}</h3>
						{#each c.prayers as p (p.id)}
							<div class="item">
								<p class="meta">{date(p.createdAt)}</p>
								{#if p.title}<p class="item-title">{p.title}</p>{/if}
								{#if p.body}<p class="body">{p.body}</p>{/if}
								{#each p.updates as u (u.at)}
									<p class="update"><span class="meta">{date(u.at)}</span> {u.text}</p>
								{/each}
							</div>
						{/each}
					{/each}
				</section>
			{/if}

			{#if showNotes && book.notes.length}
				<section class="part">
					<h2 class="part-title">{t('settings.statNotes')}</h2>
					{#each book.notes as n (n.id)}
						<div class="item">
							<p class="meta">{date(n.createdAt)}{#if n.ref}{` · ${n.ref}`}{/if}</p>
							{#if n.title}<p class="item-title">{n.title}</p>{/if}
							{#if n.source?.quote}
								<blockquote class="quote">“{n.source.quote}” <span class="meta">— {n.source.title}</span></blockquote>
							{/if}
							{#if n.body}<p class="body">{n.body}</p>{/if}
						</div>
					{/each}
				</section>
			{/if}

			{#if showDaily && book.daily.length}
				<section class="part">
					<h2 class="part-title">{t('notebook.dailyKind')}</h2>
					{#each book.daily as d (d.id)}
						<div class="item">
							<p class="meta">{date(d.createdAt)}</p>
							<p class="body">{d.body}</p>
						</div>
					{/each}
				</section>
			{/if}
		</article>
	{/if}
</div>

<style>
	.back {
		color: var(--muted);
	}
	.controls fieldset label {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		cursor: pointer;
	}
	.empty {
		margin-top: 2rem;
		font-family: var(--font-display);
		font-style: italic;
		color: var(--muted);
	}

	/* ---- The book ---------------------------------------------------- */
	.book {
		margin-top: 2rem;
		font-family: var(--font-display);
		color: var(--text);
	}
	/* On screen, each part is a page: paper on the desk, with room around it. */
	.title-page,
	.part {
		max-width: 42rem;
		margin: 0 auto 1.5rem;
		padding: 3rem 3.25rem;
		background: var(--surface);
		border: 1px solid var(--border);
		box-shadow: var(--shadow-card);
	}
	.title-page {
		min-height: 24rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
	}
	.kicker {
		font-family: var(--font-sans);
		font-size: var(--fs-eyebrow);
		letter-spacing: 0.2em;
		text-transform: uppercase;
		color: var(--muted);
	}
	.book-title {
		margin-top: 0.75rem;
		font-size: var(--fs-display);
		font-weight: 600;
		line-height: 1.15;
	}
	.range {
		margin-top: 0.75rem;
		font-style: italic;
		color: var(--muted);
	}
	.totals {
		margin-top: 1.5rem;
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 0.25rem 1.25rem;
		font-family: var(--font-sans);
		font-size: var(--fs-small);
		color: var(--muted);
	}
	.epigraph {
		margin-top: 3rem;
		max-width: 26rem;
		font-style: italic;
		color: var(--muted);
	}
	.part-title {
		margin-bottom: 1.25rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid var(--border);
		font-size: var(--fs-h2);
	}
	.month {
		margin: 1.5rem 0 0.5rem;
		font-size: var(--fs-small);
		font-style: italic;
		font-weight: 600;
		color: var(--accent);
		break-after: avoid;
	}
	.item {
		padding: 0.6rem 0 0.8rem;
		break-inside: avoid;
	}
	.item + .item {
		border-top: 1px dotted var(--border);
	}
	.meta {
		font-family: var(--font-sans);
		font-size: var(--fs-micro);
		color: var(--muted);
	}
	.item-title {
		margin-top: 0.15rem;
		font-weight: 600;
	}
	.body {
		margin-top: 0.2rem;
		white-space: pre-wrap;
		line-height: 1.6;
	}
	.answer {
		margin-top: 0.3rem;
		font-style: italic;
		color: color-mix(in srgb, var(--hl-green) 65%, var(--text));
	}
	.update {
		margin-top: 0.25rem;
		padding-inline-start: 0.75rem;
		border-inline-start: 1px dashed var(--border-strong);
		font-size: var(--fs-small);
	}
	.quote {
		margin-top: 0.3rem;
		padding-inline-start: 0.75rem;
		border-inline-start: 2px solid var(--border-strong);
		font-style: italic;
	}

	@media (max-width: 640px) {
		.title-page,
		.part {
			padding: 2rem 1.25rem;
		}
	}

	/* ---- On paper ------------------------------------------------------ */
	@media print {
		@page {
			margin: 18mm 20mm;
		}
		.controls {
			display: none;
		}
		.book {
			margin: 0;
			font-size: 11pt;
		}
		.title-page,
		.part {
			max-width: none;
			margin: 0;
			padding: 0;
			border: none;
			box-shadow: none;
			background: none;
		}
		.title-page {
			min-height: 85vh;
			break-after: page;
		}
		.part + .part {
			break-before: page;
		}
		.answer {
			color: var(--text);
		}
	}
</style>
