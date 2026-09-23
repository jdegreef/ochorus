<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import * as m from '$lib/paraglide/messages.js';
	import { HIGHLIGHT_COLORS } from '$lib/reading-schema';
	import {
		dailyStreak,
		entryTime,
		faithfulness,
		groupByDay,
		onThisDay,
		journalStats,
		prayersByPerson,
		visibleEntries,
		type PrayerGroup,
		type JournalFilter,
		type JournalKind
	} from '$lib/journal';
	import { journal } from '$lib/journal.svelte';
	import { localToday, shiftDay } from '$lib/streak';
	import { localizeHref } from '$lib/href';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EntryComposer from '$lib/components/notebook/EntryComposer.svelte';
	import JournalEntryCard from '$lib/components/notebook/JournalEntryCard.svelte';
	import ReadingClippings from '$lib/components/notebook/ReadingClippings.svelte';
	import PrayerList from '$lib/components/notebook/PrayerList.svelte';
	import FaithfulnessTimeline from '$lib/components/notebook/FaithfulnessTimeline.svelte';
	import OnThisDay from '$lib/components/notebook/OnThisDay.svelte';
	import { readJSON, writeJSON } from '$lib/persisted';

	const t = i18n.t;
	const locale = getLang();

	/**
	 * The Notebook: the reader's own writing — notes, prayers, answered prayers —
	 * on a ruled page, with everything they marked while reading pasted in below
	 * ("From my reading": highlights, margin notes, bookmarks).
	 *
	 * The index tabs are views. The dashboard's Highlights / Notes / Bookmarks
	 * tiles deep-link here with ?view=…, so those three ids keep their meaning:
	 * 'notes' shows the reader's written notes AND the margin notes on passages.
	 */
	type ReadingView = 'all' | 'notes' | 'highlights' | 'bookmarks';
	/**
	 * Every tab, and what it shows: which slice of the reader's own writing
	 * (`journal`), which of the reading clippings (`reading`), what a new entry
	 * starts as, and what an empty page says. Prayers are the reader's own, so
	 * the prayer tabs have no clippings; highlights and bookmarks no writing.
	 */
	const VIEWS = {
		all: { journal: 'all', reading: 'all', kind: 'note', empty: 'notebook.emptyJournal' },
		notes: { journal: 'notes', reading: 'notes', kind: 'note', empty: 'notebook.emptyJournal' },
		prayers: { journal: 'prayers', reading: null, kind: 'prayer', empty: 'notebook.emptyPrayers' },
		answered: { journal: 'answered', reading: null, kind: 'prayer', empty: 'notebook.emptyAnswered' },
		highlights: { journal: null, reading: 'highlights', kind: 'note', empty: '' },
		bookmarks: { journal: null, reading: 'bookmarks', kind: 'note', empty: '' }
	} satisfies Record<
		string,
		{ journal: JournalFilter | null; reading: ReadingView | null; kind: JournalKind; empty: string }
	>;
	type NotebookView = keyof typeof VIEWS;
	const isView = (v: string | null): v is NotebookView => v !== null && Object.hasOwn(VIEWS, v);
	const initialView = $page.url.searchParams.get('view');
	let view = $state<NotebookView>(isView(initialView) ? initialView : 'all');

	let query = $state('');
	let colorFilter = $state(''); // '' = all colours

	const stats = $derived(journalStats(journal.store));
	const daily = $derived(dailyStreak(journal.store, localToday()));

	// "On this day": memories from this date months and years ago. Hiding it is
	// a per-device choice for the rest of today, not reading data.
	const OTD_HIDDEN_KEY = 'ochorus:otd-hidden';
	let otdHidden = $state(readJSON<string | null>(OTD_HIDDEN_KEY, null) === localToday());
	const memories = $derived(view === 'all' && !otdHidden && !query.trim() ? onThisDay(journal.store, localToday()) : []);
	function hideOtd() {
		otdHidden = true;
		writeJSON(OTD_HIDDEN_KEY, localToday());
	}
	const TABS = $derived<{ id: NotebookView; label: string; count?: number }[]>([
		{ id: 'all', label: t('notebook.allColors') },
		{ id: 'notes', label: t('settings.statNotes'), count: stats.notes },
		{ id: 'prayers', label: t('notebook.tabPrayers'), count: stats.prayers },
		{ id: 'answered', label: t('notebook.tabAnswered'), count: stats.answered },
		{ id: 'highlights', label: t('settings.statHighlights') },
		{ id: 'bookmarks', label: t('reader.bookmarks') }
	]);

	const journalFilter = $derived<JournalFilter | null>(VIEWS[view].journal);
	const readingView = $derived<ReadingView | null>(VIEWS[view].reading);
	const newKind = $derived<JournalKind>(VIEWS[view].kind);
	// The clippings fetch every highlighted chapter, so they load the first time
	// a reading tab is open — never for a reader who stays on the prayer list —
	// and then stay mounted (hidden) so switching tabs doesn't fetch again.
	let clippingsLoaded = $state(!isView(initialView) || VIEWS[initialView].reading !== null);

	const q = $derived(query.trim());

	// The Prayers tab reads as a prayer list, by person, until the reader opens
	// one person's prayers (or asks for them by date).
	let prayerLayout = $state<'person' | 'date'>('person');
	// The Answered tab opens on the faithfulness timeline; "By date" has the cards.
	let answeredLayout = $state<'timeline' | 'date'>('timeline');
	const record = $derived(view === 'answered' ? faithfulness(journal.store, q) : null);
	const showTimeline = $derived(view === 'answered' && answeredLayout === 'timeline');
	/** One person's prayers, opened from their card; null = everyone. */
	let personFilter = $state<string | null>(null);
	const byPerson = $derived(view === 'prayers' && prayerLayout === 'person' && personFilter === null);
	const personCards = $derived(byPerson ? prayersByPerson(journal.store, q) : []);

	const entries = $derived.by(() => {
		if (!journalFilter) return [];
		const list = visibleEntries(journal.store, journalFilter, q);
		if (view !== 'prayers' || personFilter === null) return list;
		const who = personFilter.toLowerCase();
		return list.filter((e) => e.person.trim().toLowerCase() === who);
	});

	// "+ Prayer" on a person's card: a composer already addressed to them.
	let prefill = $state<{ person: string; group: PrayerGroup | '' } | undefined>(undefined);
	let composerKey = $state(0);
	function prayFor(person: string, group: PrayerGroup | '') {
		prefill = { person, group };
		composerKey += 1;
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}
	const days = $derived(groupByDay(entries, (e) => entryTime(e, journalFilter ?? 'all')));

	function setView(v: NotebookView) {
		view = v;
		if (VIEWS[v].reading) clippingsLoaded = true;
		personFilter = null;
		prefill = undefined;
		if (v === 'bookmarks') colorFilter = '';
		// Keep the view in the URL so it's shareable and survives the reload a
		// language change triggers (mirrors Settings' ?section=).
		const url = new URL($page.url);
		if (v === 'all') url.searchParams.delete('view');
		else url.searchParams.set('view', v);
		goto(url, { replaceState: true, keepFocus: true, noScroll: true });
	}

	const today = new Date();
	const todayKey = localToday(today);
	const yesterdayKey = shiftDay(todayKey, -1);
	const longDate = (at: number | Date) =>
		new Date(at).toLocaleDateString(locale, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
	function dayLabel(day: string, at: number): string {
		if (day === todayKey) return t('plans.today');
		if (day === yesterdayKey) return t('notebook.yesterday');
		return longDate(at);
	}

	const emptyMessage = $derived(t(VIEWS[view].empty));
</script>

<svelte:head><title>{t('notebook.title')} — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="page-col px-5 py-10">
	<div class="notebook">
		<!-- The index tabs along the top edge of the page. -->
		<div class="tabs" role="group" aria-label={t('notebook.filterType')}>
			{#each TABS as tab (tab.id)}
				<button
					class="tab tab-{tab.id}"
					class:active={view === tab.id}
					aria-pressed={view === tab.id}
					onclick={() => setView(tab.id)}
				>
					{tab.label}{#if tab.count}<span class="count">{tab.count}</span>{/if}
				</button>
			{/each}
		</div>

		<div class="paper">
			<div class="paper-head">
				<PageHeader title={t('notebook.title')} tagline={t('notebook.subtitle')} />
				<p class="today text-small">{longDate(today)}</p>
			</div>

			{#if record && record.answered > 0}
				<p class="praise">
					✦ {record.answered === 1 ? t('notebook.praiseOne') : m.notebook_praise_many({ n: String(record.answered) })}
				</p>
				<!-- The record at a glance: answered, still praying, how long answers take. -->
				<dl class="tiles">
					<div class="tile">
						<dt>{t('notebook.tabAnswered')}</dt>
						<dd>{record.answered}</dd>
					</div>
					<div class="tile">
						<dt>{t('notebook.statPraying')}</dt>
						<dd>{record.praying}</dd>
					</div>
					<div class="tile">
						<dt>{t('notebook.statAvgDays')}</dt>
						<dd>{record.avgDays ?? '—'}</dd>
					</div>
				</dl>
			{/if}

			{#if view === 'all' || view === 'prayers'}
				<!-- The daily prayer: a few guided minutes, and the days kept in a row. -->
				<a class="daily-card" href={localizeHref('/notebook/today')}>
					<span class="daily-sun" aria-hidden="true">☀</span>
					<span class="min-w-0 grow">
						<span class="block font-semibold text-text">{t('notebook.dailyTitle')}</span>
						<span class="block text-small text-muted">
							{#if daily.doneToday}✓ {t('notebook.dailyDone')}{:else}{t('notebook.dailyIntro')}{/if}
						</span>
					</span>
					{#if daily.streak}
						<span class="daily-streak text-small"><span aria-hidden="true" class="me-1">🔥</span>{daily.streak}</span>
					{/if}
					<span class="btn btn-sm" class:btn-primary={!daily.doneToday}>
						{daily.doneToday ? t('notebook.dailyAgain') : t('notebook.dailyBegin')}
					</span>
				</a>
			{/if}

			{#if memories.length}
				<OnThisDay {memories} onhide={hideOtd} />
			{/if}

			<input
				type="search"
				bind:value={query}
				placeholder={t('notebook.search')}
				aria-label={t('notebook.search')}
				class="field mb-6 w-full"
			/>

			{#if journalFilter}
				<section aria-label={t('notebook.myWriting')}>
					<!-- Keyed on the kind so switching to the Prayers tab starts a prayer. -->
					{#key `${newKind}:${composerKey}`}
						<EntryComposer
							kind={newKind}
							initial={prefill ? { kind: 'prayer', ...prefill } : undefined}
							onsave={(d) => {
								journal.add(d);
								prefill = undefined;
							}}
							oncancel={prefill
								? () => {
										prefill = undefined;
										composerKey += 1;
									}
								: undefined}
						/>
					{/key}

					{#if view === 'prayers'}
						<div class="mt-6 flex flex-wrap items-center gap-3">
							{#if personFilter !== null}
								<button class="chip" onclick={() => (personFilter = null)}>
									← {t('notebook.allPeople')}
								</button>
								<span class="text-small font-semibold text-text">{personFilter || t('notebook.forAnyone')}</span>
							{:else}
								<div class="seg" role="group" aria-label={t('notebook.prayerLayout')}>
									<button
										class:active={prayerLayout === 'person'}
										aria-pressed={prayerLayout === 'person'}
										onclick={() => (prayerLayout = 'person')}>{t('notebook.byPerson')}</button
									>
									<button
										class:active={prayerLayout === 'date'}
										aria-pressed={prayerLayout === 'date'}
										onclick={() => (prayerLayout = 'date')}>{t('notebook.byDate')}</button
									>
								</div>
							{/if}
						</div>
					{/if}

					{#if view === 'answered' && stats.answered > 0}
						<div class="mt-6 flex">
							<div class="seg" role="group" aria-label={t('notebook.answeredLayout')}>
								<button
									class:active={answeredLayout === 'timeline'}
									aria-pressed={answeredLayout === 'timeline'}
									onclick={() => (answeredLayout = 'timeline')}>{t('notebook.timeline')}</button
								>
								<button
									class:active={answeredLayout === 'date'}
									aria-pressed={answeredLayout === 'date'}
									onclick={() => (answeredLayout = 'date')}>{t('notebook.byDate')}</button
								>
							</div>
						</div>
					{/if}

					{#if showTimeline && record?.months.length}
						<FaithfulnessTimeline months={record.months} {locale} />
					{:else if byPerson && personCards.length}
						<PrayerList cards={personCards} {locale} onopen={(p) => (personFilter = p)} onpray={prayFor} />
					{:else if entries.length === 0}
						<p class="empty">{q ? t('notebook.no_matches') : emptyMessage}</p>
					{:else}
						{#each days as d (d.day)}
							<h2 class="day">{dayLabel(d.day, d.at)}</h2>
							<div class="entries">
								{#each d.entries as e (e.id)}
									<JournalEntryCard entry={e} {locale} />
								{/each}
							</div>
						{/each}
					{/if}
				</section>
			{/if}

			{#if clippingsLoaded}
				<section class="reading" class:solo={!journalFilter} hidden={!readingView} aria-labelledby="from-reading">
					<div class="mb-4 flex flex-wrap items-center justify-between gap-3">
						<h2 id="from-reading" class="text-h2">{t('notebook.fromReading')}</h2>
						<!-- Colours only make sense where highlights show. -->
						{#if readingView !== 'bookmarks'}
							<div class="flex items-center gap-2" role="group" aria-label={t('notebook.filterColor')}>
								<button
									class="chip"
									class:active={colorFilter === ''}
									onclick={() => (colorFilter = '')}
									aria-pressed={colorFilter === ''}
								>
									{t('notebook.allColors')}
								</button>
								{#each HIGHLIGHT_COLORS as color (color)}
									<button
										class="hl-swatch"
										data-color={color}
										class:active={colorFilter === color}
										onclick={() => (colorFilter = colorFilter === color ? '' : color)}
										aria-pressed={colorFilter === color}
										aria-label="{t('notebook.filterColor')}: {t(`reader.hl_${color}`)}"
										title={t(`reader.hl_${color}`)}
									></button>
								{/each}
							</div>
						{/if}
					</div>
					<ReadingClippings view={readingView ?? 'all'} {query} {colorFilter} />
				</section>
			{/if}
		</div>
	</div>
</div>

<style>
	.notebook {
		--margin-x: 3.25rem;
		--rule-gap: 2rem;
		/* The binding's hole column sits in the gutter before the margin line. */
		--binding: 1.6rem;
	}

	/* ---- Index tabs ---------------------------------------------------- */
	.tabs {
		display: flex;
		gap: 0.25rem;
		padding-inline-start: calc(var(--margin-x) - 0.5rem);
		overflow-x: auto;
		scrollbar-width: none;
		/* Tabs tuck under the paper's top edge by the border's width. */
		margin-bottom: -1px;
		position: relative;
		z-index: 1;
	}
	.tabs::-webkit-scrollbar {
		display: none;
	}
	.tab {
		--tab-hue: var(--accent);
		flex: none;
		display: inline-flex;
		align-items: baseline;
		gap: 0.35rem;
		padding: 0.5rem 0.9rem 0.45rem;
		border: 1px solid var(--border);
		border-bottom: none;
		border-top: 3px solid color-mix(in srgb, var(--tab-hue) 55%, transparent);
		border-radius: 8px 8px 0 0;
		background: var(--surface-2);
		color: var(--muted);
		font-size: var(--fs-small);
		font-weight: 600;
		cursor: pointer;
		transform: translateY(3px);
		transition:
			transform var(--duration-fast) ease,
			color var(--duration-fast) ease;
	}
	.tab:hover {
		color: var(--text);
		transform: translateY(1px);
	}
	.tab.active {
		background: var(--surface);
		color: var(--text);
		border-top-color: var(--tab-hue);
		transform: none;
		padding-bottom: calc(0.45rem + 1px);
	}
	.tab-prayers {
		--tab-hue: var(--gold);
	}
	.tab-answered {
		--tab-hue: var(--hl-green);
	}
	.tab-highlights {
		--tab-hue: var(--hl-rose);
	}
	.tab-bookmarks {
		--tab-hue: var(--hl-blue);
	}

	/* ---- The page ------------------------------------------------------ */
	.paper {
		position: relative;
		padding-block: 2rem 3rem;
		padding-inline: calc(var(--margin-x) + 1.25rem) 1.5rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 4px 10px 10px 4px;
		box-shadow:
			var(--shadow-card),
			/* the edges of the pages beneath this one */ 3px 3px 0 -1px var(--surface-2),
			3px 3px 0 0 var(--border),
			6px 6px 0 -1px var(--surface-2),
			6px 6px 0 0 var(--border);
		min-height: 60vh;
	}
	:global([dir='rtl']) .paper {
		border-radius: 10px 4px 4px 10px;
	}
	/* The red margin line. */
	.paper::after {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		inset-inline-start: var(--margin-x);
		width: 0;
		border-inline-start: 1.5px solid color-mix(in srgb, var(--danger) 45%, transparent);
		pointer-events: none;
	}
	/* Spiral binding: a punched hole in the page for each coil, and the wire
	   loop itself standing proud of the page's edge. */
	.paper::before {
		content: '';
		position: absolute;
		top: 1.25rem;
		bottom: 1.25rem;
		inset-inline-start: calc(var(--binding) * -0.55);
		width: calc(var(--binding) * 1.4);
		background-image:
			radial-gradient(
				ellipse 42% 30% at 50% 50%,
				transparent 62%,
				color-mix(in srgb, var(--muted) 85%, transparent) 64% 88%,
				transparent 92%
			),
			radial-gradient(circle at 72% 50%, var(--bg) 0 0.22rem, transparent 0.25rem);
		background-size: 100% 1.5rem;
		background-repeat: repeat-y;
		pointer-events: none;
	}

	.paper-head {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: 0 1.5rem;
		align-items: flex-start;
	}
	.today {
		font-family: var(--font-display);
		font-style: italic;
		color: var(--muted);
		padding-top: 0.6rem;
	}

	.tiles {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 0.6rem;
		margin-bottom: 1.25rem;
	}
	.tile {
		padding: 0.7rem 0.85rem;
		border-radius: var(--radius-sm);
		background: var(--surface-2);
	}
	.tile dt {
		font-size: var(--fs-micro);
		color: var(--muted);
	}
	.tile dd {
		font-family: var(--font-display);
		font-size: var(--fs-h2);
		font-weight: 600;
		line-height: 1.2;
		color: var(--text);
	}
	.praise {
		margin: 0 0 1.25rem;
		padding: 0.6rem 0.9rem;
		border-radius: var(--radius-sm);
		background: color-mix(in srgb, var(--hl-green) 10%, transparent);
		color: color-mix(in srgb, var(--hl-green) 65%, var(--text));
		font-family: var(--font-display);
		font-style: italic;
	}

	.daily-card {
		display: flex;
		align-items: center;
		gap: 0.85rem;
		margin-bottom: 1.25rem;
		padding: 0.85rem 1rem;
		border: 1px solid color-mix(in srgb, var(--gold) 40%, transparent);
		border-radius: var(--radius-sm);
		background: color-mix(in srgb, var(--gold) 9%, var(--surface));
		color: inherit;
	}
	.daily-card:hover {
		text-decoration: none;
		border-color: var(--gold);
	}
	.daily-sun {
		flex: none;
		font-size: var(--fs-h2);
		color: var(--gold);
	}
	.daily-streak {
		flex: none;
		color: var(--warning);
		font-weight: 700;
	}
	.day {
		margin: 2.25rem 0 0.75rem;
		font-family: var(--font-display);
		font-size: var(--fs-small);
		font-weight: 600;
		font-style: italic;
		letter-spacing: 0.02em;
		color: var(--accent);
		border-bottom: 1px solid var(--border);
		padding-bottom: 0.25rem;
	}
	.entries {
		display: grid;
		gap: 1.75rem;
	}
	.empty {
		margin-top: 1.5rem;
		font-family: var(--font-display);
		font-style: italic;
		color: var(--muted);
		line-height: var(--rule-gap);
	}

	.reading {
		margin-top: 3.5rem;
		padding-top: 2rem;
		/* A perforated tear line between the writing and the pasted-in clippings. */
		border-top: 2px dashed var(--border-strong);
	}
	.reading.solo {
		margin-top: 0;
		padding-top: 0;
		border-top: none;
	}

	@media (max-width: 640px) {
		.notebook {
			--margin-x: 1.75rem;
			--binding: 1.2rem;
		}
		.paper {
			padding-block: 1.5rem 2.5rem;
			padding-inline: calc(var(--margin-x) + 0.85rem) 1rem;
		}
		.tabs {
			padding-inline-start: 0.25rem;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.tab {
			transition: none;
			transform: none;
		}
	}
</style>
