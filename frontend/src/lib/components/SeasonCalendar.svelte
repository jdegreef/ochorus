<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { watchToday } from '$lib/today';
	import { dateKey } from '$lib/dailyDate';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { lookupScripture } from '$lib/scripture.svelte';
	import { doorPath, loadCalendar, type Calendar, type Door } from '$lib/seasonCalendar';
	import SectionHeader from '$lib/components/SectionHeader.svelte';

	/**
	 * The Advent / Lent calendar (design #34) on /today: a door for each day of
	 * the season ($lib/seasonCalendar). Past doors stand open on the day's
	 * reading and its Scripture reference; today's is lit and leads, with its
	 * reading set out above the grid (in English with the verse in the house
	 * Bible's words, tagged OWB); later doors are shut and say when they open.
	 * Out of season, or in a language with too few of the season's readings,
	 * it draws nothing. Client-side, on the reader's local date: /today is a
	 * prerendered shell, and a baked calendar would freeze on the build day.
	 */
	const t = i18n.t;
	const lang = getLang();

	let cal = $state<Calendar | null>(null);
	let verse = $state('');
	let shownFor = '';

	async function show(now: Date) {
		const key = dateKey(now);
		if (key === shownFor) return;
		shownFor = key;
		const next = await loadCalendar(now, lang);
		if (key !== shownFor) return;
		// No calendar costs no fetch to ask again (out of season, or a cached
		// shelf), and a failed fetch must be asked again — so look next time.
		if (!next) shownFor = '';
		const first = !cal && next;
		cal = next;
		verse = '';
		// The Today card links here as /today#calendar, but the section is drawn
		// only now, after the browser and the router looked for the anchor.
		if (first && location.hash === '#calendar') {
			await tick();
			document.getElementById('calendar')?.scrollIntoView();
		}
		const ref = next?.today?.owbRef;
		if (ref) {
			const hit = await lookupScripture(ref);
			if (key === shownFor && hit?.verses.length) verse = hit.verses.map((v) => v.text).join(' ');
		}
	}

	onMount(() => watchToday((now) => void show(now)));

	const DAY_MS = 86_400_000;
	const fmt = (opts: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat(lang, { ...opts, timeZone: 'UTC' });
	const LONG = fmt({ weekday: 'long', day: 'numeric', month: 'long' });
	const NUM = fmt({ day: 'numeric' });
	const longDate = (d: Door) => LONG.format(d.day * DAY_MS);
	const dayNum = (d: Door) => NUM.format(d.day * DAY_MS);

	const isAdvent = $derived(cal?.window.season === 'advent');
	const href = (d: Door) => localizeHref(doorPath(d));
	/** The reference, tagged with the Bible its words are read in when the
	 *  house Bible's words are shown under it (English only). */
	const refLine = (d: Door) => (d.ref && verse ? `${d.ref} · OWB` : d.ref);
</script>

{#if cal}
	<section id="calendar" class="calendar mt-8" aria-label={t(isAdvent ? 'calendar.adventTitle' : 'calendar.lentTitle')}>
		<SectionHeader
			title={t(isAdvent ? 'calendar.adventTitle' : 'calendar.lentTitle')}
			subtitle={t(isAdvent ? 'calendar.adventTagline' : 'calendar.lentTagline')}
		/>

		{#if cal.today}
			{@const d = cal.today}
			<div class="today-door rounded-2xl border border-border bg-surface px-5 py-5 sm:px-6">
				<p class="eyebrow text-accent">{t('calendar.todayDoor')} · {longDate(d)}</p>
				<p class="mt-2 text-h3 font-display" dir="auto">{d.title}</p>
				{#if d.source || d.ref}
					<p class="mt-1 text-small text-muted" dir="auto">
						{[d.source, refLine(d)].filter(Boolean).join(' · ')}
					</p>
				{/if}
				{#if verse}
					<p class="verse mt-3 line-clamp-4 text-body" lang="en">{verse}</p>
				{/if}
				<a class="btn btn-primary btn-solid btn-sm mt-4" href={href(d)}>{t('calendar.read')}</a>
			</div>
		{/if}

		<ol class="doors mt-6" role="list">
			{#each cal.doors as d (d.n)}
				<li>
					{#if d.state === 'open'}
						<a class="door open" href={href(d)} aria-label="{longDate(d)}: {d.title}">
							<span class="num" aria-hidden="true">{dayNum(d)}</span>
							<span class="door-title line-clamp-3" dir="auto" aria-hidden="true">{d.title}</span>
							{#if d.ref}<span class="door-ref truncate" dir="auto" aria-hidden="true">{d.ref}</span>{/if}
						</a>
					{:else if d.state === 'today'}
						<a
							class="door today"
							href={href(d)}
							aria-current="date"
							aria-label="{t('calendar.today')}, {longDate(d)}: {d.title}"
						>
							<span class="big-num" aria-hidden="true">{dayNum(d)}</span>
							<span class="today-label" aria-hidden="true">{t('calendar.today')}</span>
						</a>
					{:else}
						<span class="door locked">
							<span class="big-num" aria-hidden="true">{dayNum(d)}</span>
							<span class="sr-only">{t('calendar.locked').replace('%date%', longDate(d))}</span>
						</span>
					{/if}
				</li>
			{/each}
		</ol>
	</section>
{/if}

<style>
	.calendar {
		scroll-margin-top: 5rem;
	}
	.today-door {
		max-width: 40rem;
		margin-bottom: 0.5rem;
	}
	.font-display {
		font-family: var(--font-display);
		font-weight: 500;
		text-wrap: balance;
	}
	/* Read, not scanned — and no italic: Arabic, Amharic and Hindi have none. */
	.verse {
		font-family: var(--font-display);
	}
	/* Doors in rows of whatever fits: four on a phone, six or seven wider. */
	.doors {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 5.25rem), 1fr));
		gap: 0.5rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.door {
		position: relative;
		display: flex;
		flex-direction: column;
		aspect-ratio: 1;
		border-radius: var(--radius-sm);
		border: 1px solid var(--color-border);
		background: var(--color-surface);
		color: var(--color-text);
		text-decoration: none;
		overflow: hidden;
	}
	.big-num {
		margin: auto;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}
	/* An open door: the accent ground, the day's reading written on it. */
	.door.open {
		gap: 0.15rem;
		padding: 0.4rem 0.45rem;
		background: var(--color-accent);
		border-color: var(--color-accent);
		color: var(--color-accent-contrast);
		font-size: var(--fs-micro);
		line-height: 1.25;
	}
	.door.open .num {
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		opacity: 0.85;
	}
	.door-title {
		font-weight: 600;
		text-wrap: balance;
	}
	.door-ref {
		margin-top: auto;
		opacity: 0.85;
	}
	/* Today's: still shut, but lit — the one to open. */
	.door.today {
		border-color: var(--color-gold);
		outline: 2px solid var(--color-gold);
		outline-offset: 2px;
	}
	.today-label {
		position: absolute;
		inset-inline: 0;
		bottom: 0.35rem;
		text-align: center;
		font-size: var(--fs-micro);
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--color-muted);
	}
	.door.locked {
		border-style: dashed;
		color: var(--color-muted);
		opacity: 0.6;
	}
	.door.open:hover,
	.door.open:focus-visible {
		filter: brightness(1.08);
	}
	/* The lit door swings ajar under the pointer — only where motion is
	   welcome (the global reduced-motion rule would freeze it anyway). */
	@media (prefers-reduced-motion: no-preference) {
		.door.today {
			transform-origin: left center;
			transition: transform var(--duration-fast) ease-out;
		}
		:global([dir='rtl']) .door.today {
			transform-origin: right center;
		}
		.door.today:hover,
		.door.today:focus-visible {
			transform: perspective(30rem) rotateY(-14deg);
		}
		:global([dir='rtl']) .door.today:hover,
		:global([dir='rtl']) .door.today:focus-visible {
			transform: perspective(30rem) rotateY(14deg);
		}
	}
</style>
