<script lang="ts">
	import { untrack } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { absUrl } from '$lib/seo';
	import { downloadFile } from '$lib/dataExport';
	import { readJSON, writeJSON } from '$lib/persisted';
	import { buildScheduleICS } from '$lib/reminder';
	import {
		READING_DAYS,
		isoDay,
		monthGrid,
		parseIsoDay,
		schedulePlan,
		type ReadingDays
	} from '$lib/planSchedule';
	import type { PlanDay, PlanDetail } from '$lib/library-public';
	import Icon from './Icon.svelte';

	/**
	 * A plan on real dates: the days still to read laid on a month grid from a
	 * start date (today once started, or one the reader picks), on the weekdays
	 * they read — with when each book begins and ends, the finish date, and the
	 * whole schedule as a calendar file whose events carry a morning reminder.
	 *
	 * Client-only by nature (it is about the reader's today), so the page shows
	 * it only after mount. The reader's choices are a per-viewer convenience in
	 * localStorage — never progress, which planProgress owns.
	 */
	let {
		plan,
		today,
		started,
		doneSet,
		sections,
		dayHref,
		dayTitle
	}: {
		plan: PlanDetail;
		today: Date;
		started: boolean;
		doneSet: Set<number>;
		/** The plan's book runs, named as the page names them, for the milestones. */
		sections: { key: string; label: string; days: PlanDay[] }[];
		dayHref: (day: number) => string;
		dayTitle: (d: PlanDay) => string;
	} = $props();

	const t = i18n.t;
	const KEY = 'ochorus:plan-schedule';
	type Prefs = { start?: string; rule?: ReadingDays; time?: string };
	const saved = (() => readJSON<Record<string, Prefs>>(KEY, {})[plan.slug] ?? {})();

	let rule = $state<ReadingDays>(saved.rule && READING_DAYS.includes(saved.rule) ? saved.rule : 'daily');
	// Seeded once from what was saved (or today): the input's own working value.
	let startIso = $state(untrack(() => (saved.start && parseIsoDay(saved.start) ? saved.start : isoDay(today))));
	let time = $state(saved.time ?? '07:00');
	$effect(() => {
		const all = readJSON<Record<string, Prefs>>(KEY, {});
		all[plan.slug] = { start: startIso, rule, time };
		writeJSON(KEY, all);
	});

	const RULE_LABEL: Record<ReadingDays, string> = {
		daily: 'plans.everyDay',
		weekdays: 'plans.weekdays',
		monsat: 'plans.monSat'
	};

	/** A started plan runs from today; a new one from the chosen start. */
	const start = $derived(started ? today : (parseIsoDay(startIso) ?? today));
	const byDay = $derived(new Map(plan.days.map((d) => [d.day, d])));
	const schedule = $derived(
		schedulePlan(
			plan.days.filter((d) => !doneSet.has(d.day)).map((d) => d.day),
			start,
			rule
		)
	);
	const byDate = $derived(new Map(schedule.map((s) => [isoDay(s.date), byDay.get(s.day)!])));
	const dateOf = $derived(new Map(schedule.map((s) => [s.day, s.date])));

	const fmt = $derived({
		long: new Intl.DateTimeFormat(getLang(), { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }),
		short: new Intl.DateTimeFormat(getLang(), { month: 'short', day: 'numeric' }),
		month: new Intl.DateTimeFormat(getLang(), { month: 'long', year: 'numeric' }),
		weekday: new Intl.DateTimeFormat(getLang(), { weekday: 'short' })
	});
	// Monday-first headers, from a known Monday (5 Oct 2026).
	const weekdays = $derived(Array.from({ length: 7 }, (_, i) => fmt.weekday.format(new Date(2026, 9, 5 + i))));

	/** The month on show: the first scheduled one, until the reader pages. */
	let shown = $state<{ y: number; m: number } | null>(null);
	const month = $derived(shown ?? { y: (schedule[0]?.date ?? today).getFullYear(), m: (schedule[0]?.date ?? today).getMonth() });
	const weeks = $derived(monthGrid(month.y, month.m));
	const page = (step: number) => {
		const d = new Date(month.y, month.m + step, 1);
		shown = { y: d.getFullYear(), m: d.getMonth() };
	};
	const todayIso = $derived(isoDay(today));

	/** When each book's remaining days begin and end — or that it is read. */
	const milestones = $derived(
		sections.map((s) => {
			const dates = s.days.map((d) => dateOf.get(d.day)).filter((d): d is Date => !!d);
			return {
				key: s.key,
				label: s.label,
				range: dates.length ? `${fmt.short.format(dates[0])} – ${fmt.short.format(dates.at(-1)!)}` : ''
			};
		})
	);

	const download = () => {
		const ics = buildScheduleICS(
			schedule.map((s) => {
				const d = byDay.get(s.day)!;
				return {
					date: s.date,
					summary: `${t('plans.day')} ${s.day} · ${dayTitle(d)} — ${plan.title}`,
					url: absUrl(dayHref(s.day))
				};
			}),
			time,
			{ now: new Date(), uidPrefix: `ochorus-plan-${plan.slug}-${isoDay(start)}` }
		);
		downloadFile(`${plan.slug}.ics`, 'text/calendar;charset=utf-8', ics);
	};
</script>

<div class="plan-cal">
	<!-- The schedule's levers: when to start (a new plan only) and which days. -->
	<div class="cal-controls">
		{#if !started}
			<label class="cal-field">
				<span class="text-eyebrow text-muted">{t('plans.startOn')}</span>
				<input class="field" type="date" bind:value={startIso} min={isoDay(today)} />
			</label>
		{/if}
		<div class="cal-field">
			<span class="text-eyebrow text-muted" id="read-on-label">{t('plans.readOn')}</span>
			<div class="seg" role="group" aria-labelledby="read-on-label">
				{#each READING_DAYS as r (r)}
					<button type="button" class:active={rule === r} aria-pressed={rule === r} onclick={() => (rule = r)}
						>{t(RULE_LABEL[r])}</button
					>
				{/each}
			</div>
		</div>
		{#if schedule.length}
			<p class="cal-finish">
				<span class="block text-eyebrow text-muted">{t('plans.finishOn')}</span>
				<span class="font-display text-h3 font-semibold text-text">{fmt.long.format(schedule.at(-1)!.date)}</span>
			</p>
		{/if}
	</div>

	<div class="cal-body">
		<section class="min-w-0 flex-1" aria-labelledby="cal-month">
			<div class="mb-2 flex items-center justify-between">
				<button type="button" class="btn btn-ghost btn-icon" onclick={() => page(-1)} aria-label={t('plans.prevMonth')}>
					<Icon name="chevron-left" size={18} />
				</button>
				<h3 id="cal-month" class="font-display text-h3 font-semibold" aria-live="polite">
					{fmt.month.format(new Date(month.y, month.m, 1))}
				</h3>
				<button type="button" class="btn btn-ghost btn-icon" onclick={() => page(1)} aria-label={t('plans.nextMonth')}>
					<Icon name="chevron-right" size={18} />
				</button>
			</div>
			<div class="cal-grid" role="grid" aria-labelledby="cal-month">
				<div class="contents" role="row">
					{#each weekdays as w (w)}<span class="cal-dow text-micro text-muted" role="columnheader">{w}</span>{/each}
				</div>
				{#each weeks as week (isoDay(week[0]))}
					<div class="contents" role="row">
						{#each week as date (isoDay(date))}
							{@const iso = isoDay(date)}
							{@const d = byDate.get(iso)}
							{@const out = date.getMonth() !== month.m}
							<div role="gridcell" class="cal-cell" class:out class:today={iso === todayIso}>
								<span class="cal-date tabular-nums">{date.getDate()}</span>
								{#if d}
									<a href={dayHref(d.day)} class="cal-reading" dir="auto">
										<span class="block text-micro text-muted">{t('plans.day')} {d.day}</span>
										<span class="cal-title">{dayTitle(d)}</span>
									</a>
								{/if}
							</div>
						{/each}
					</div>
				{/each}
			</div>
		</section>

		<aside class="cal-side">
			{#if sections.length > 1}
				<h3 class="section-heading">{t('plans.milestones')}</h3>
				<ul class="mb-5 space-y-2">
					{#each milestones as ms (ms.key)}
						<li class="flex items-baseline justify-between gap-3 text-small">
							<span class="min-w-0 truncate font-medium text-text" dir="auto">{ms.label}</span>
							<span class="shrink-0 tabular-nums text-muted">{ms.range || '✓'}</span>
						</li>
					{/each}
				</ul>
			{/if}
			{#if schedule.length}
				<!-- The schedule on the reader's own calendar: one event a reading,
				     each with an alert that morning — no account, no server. -->
				<label class="cal-field">
					<span class="text-eyebrow text-muted">{t('plans.remindAt')}</span>
					<input class="field" type="time" bind:value={time} />
				</label>
				<button type="button" class="btn mt-3 w-full" onclick={download}>
					<Icon name="calendar" size={16} />{t('plans.addCalendar')}
				</button>
				<p class="mt-2 text-micro text-muted">{t('plans.calendarHint')}</p>
			{/if}
		</aside>
	</div>
</div>

<style>
	.cal-controls {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: 1rem 1.5rem;
		margin-bottom: 1.25rem;
	}
	.cal-field {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}
	.cal-finish {
		margin-inline-start: auto;
		text-align: end;
	}
	.cal-body {
		display: flex;
		flex-wrap: wrap;
		gap: 1.5rem;
	}
	.cal-body > section {
		flex: 999 1 26rem;
	}
	.cal-side {
		flex: 1 1 14rem;
	}
	.cal-grid {
		display: grid;
		grid-template-columns: repeat(7, minmax(0, 1fr));
		gap: 0.25rem;
	}
	.cal-dow {
		padding-block: 0.25rem;
		text-align: center;
	}
	.cal-cell {
		display: flex;
		flex-direction: column;
		min-height: 5rem;
		padding: 0.375rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--surface);
		overflow: hidden;
	}
	.cal-cell.out {
		opacity: 0.4;
	}
	.cal-cell.today {
		border-color: var(--accent);
		background: var(--accent-soft);
	}
	.cal-date {
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--text);
	}
	.cal-reading {
		margin-top: 0.25rem;
		color: var(--text);
	}
	.cal-reading:hover {
		text-decoration: none;
	}
	.cal-reading:hover .cal-title {
		color: var(--accent);
	}
	.cal-title {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		font-size: var(--fs-micro);
		line-height: 1.35;
	}
	/* A phone's month: the date and a dot, the title left to the list view. */
	@media (max-width: 639.98px) {
		.cal-cell {
			min-height: 3rem;
			padding: 0.25rem;
		}
		.cal-title {
			display: none;
		}
	}
</style>
