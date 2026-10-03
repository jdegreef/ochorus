<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { absUrl } from '$lib/seo';
	import { downloadFile } from '$lib/dataExport';
	import { planSchedules } from '$lib/planSchedules.svelte';
	import { buildScheduleICS, readReminderTime } from '$lib/reminder';
	import { localToday } from '$lib/streak';
	import { READING_DAYS, monthGrid, parseIsoDay, schedulePlan, weekStart, type ReadingDays } from '$lib/planSchedule';
	import type { PlanDay, PlanDetail } from '$lib/library-public';
	import Icon from './Icon.svelte';

	/**
	 * A plan on real dates: the days still to read laid on a month grid from a
	 * start date (today once started, or one the reader picks), on the weekdays
	 * they read — with when each book begins and ends, the finish date, and the
	 * whole schedule as a calendar file whose events carry a morning reminder.
	 *
	 * Client-only by nature (it is about the reader's today), so the page shows
	 * it only after mount. The reader's choices live in `planSchedules`, which
	 * syncs them to their account — so they follow the reader across devices,
	 * and a choice made elsewhere shows here after a sync. Never progress,
	 * which planProgress owns.
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
	// The reader's choices, read live from the synced store (another device's
	// choice lands here after a merge); the controls write straight back to it.
	const prefs = $derived(planSchedules.get(plan.slug));
	const rule = $derived<ReadingDays>(prefs.rule && READING_DAYS.includes(prefs.rule) ? prefs.rule : 'daily');
	// Alerts default to the daily reminder time the reader set in Settings.
	const time = $derived(prefs.time ?? readReminderTime());
	const todayIso = $derived(localToday(today));
	// A chosen start that has since passed gives way to today.
	const startIso = $derived(prefs.start && parseIsoDay(prefs.start) && prefs.start >= todayIso ? prefs.start : todayIso);

	const RULE_LABEL: Record<ReadingDays, string> = {
		daily: 'plans.everyDay',
		weekdays: 'plans.weekdays',
		monsat: 'plans.monSat'
	};

	/** A started plan runs from today; a new one from the chosen start. */
	const start = $derived((!started && parseIsoDay(startIso)) || today);
	const schedule = $derived(
		schedulePlan(
			plan.days.filter((d) => !doneSet.has(d.day)),
			start,
			rule
		)
	);
	const byDate = $derived(new Map(schedule.map((s) => [localToday(s.date), s.item])));
	const dateOf = $derived(new Map(schedule.map((s) => [s.item.day, s.date])));
	const fmt = $derived({
		long: new Intl.DateTimeFormat(getLang(), { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }),
		short: new Intl.DateTimeFormat(getLang(), { month: 'short', day: 'numeric' }),
		month: new Intl.DateTimeFormat(getLang(), { month: 'long', year: 'numeric' }),
		weekday: new Intl.DateTimeFormat(getLang(), { weekday: 'short' })
	});

	/** The month on show: the schedule's first, paged from there by the reader. */
	let offset = $state(0);
	const anchor = $derived(schedule[0]?.date ?? today);
	const month = $derived(new Date(anchor.getFullYear(), anchor.getMonth() + offset, 1));
	// The week starts where the reader's locale starts it (Sunday in the US).
	const weeks = $derived(monthGrid(month.getFullYear(), month.getMonth(), weekStart(getLang())));

	/** When each book's remaining days begin and end — null once it is read. */
	const milestones = $derived(
		sections.map((s) => {
			const dates = s.days.map((d) => dateOf.get(d.day)).filter((d): d is Date => !!d);
			return {
				key: s.key,
				label: s.label,
				range: dates.length ? `${fmt.short.format(dates[0])} – ${fmt.short.format(dates.at(-1)!)}` : null
			};
		})
	);

	const download = () => {
		const ics = buildScheduleICS(
			schedule.map(({ item, date }) => ({
				date,
				summary: `${t('plans.day')} ${item.day} · ${dayTitle(item)} — ${plan.title}`,
				url: absUrl(dayHref(item.day))
			})),
			time,
			{ now: new Date(), uidPrefix: `ochorus-plan-${plan.slug}-${localToday(start)}` }
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
				<input
					class="field"
					type="date"
					value={startIso}
					min={todayIso}
					onchange={(e) => {
						offset = 0;
						planSchedules.set(plan.slug, { start: e.currentTarget.value });
					}}
				/>
			</label>
		{/if}
		<div class="cal-field">
			<span class="text-eyebrow text-muted" id="read-on-label">{t('plans.readOn')}</span>
			<div class="seg" role="group" aria-labelledby="read-on-label">
				{#each READING_DAYS as r (r)}
					<button
						type="button"
						class:active={rule === r}
						aria-pressed={rule === r}
						onclick={() => planSchedules.set(plan.slug, { rule: r })}>{t(RULE_LABEL[r])}</button
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
		<section class="min-w-0" aria-labelledby="cal-month">
			<div class="mb-2 flex items-center justify-between">
				<button type="button" class="btn btn-ghost btn-icon" onclick={() => offset--} aria-label={t('plans.prevMonth')}>
					<Icon name="chevron-left" size={18} />
				</button>
				<h3 id="cal-month" class="font-display text-h3 font-semibold" aria-live="polite">
					{fmt.month.format(month)}
				</h3>
				<button type="button" class="btn btn-ghost btn-icon" onclick={() => offset++} aria-label={t('plans.nextMonth')}>
					<Icon name="chevron-right" size={18} />
				</button>
			</div>
			<!-- A picture of the month, not a widget: each reading is a link that
			     names its full date, so a screen reader hears the schedule as a
			     list of links rather than a grid it can't move through. -->
			<div class="cal-grid">
				{#each weeks[0] as d (d.iso)}
					<span class="cal-dow text-micro text-muted" aria-hidden="true">{fmt.weekday.format(d.date)}</span>
				{/each}
				{#each weeks.flat() as cell (cell.iso)}
					{@const d = byDate.get(cell.iso)}
					<div class="cal-cell" class:out={cell.date.getMonth() !== month.getMonth()} class:today={cell.iso === todayIso}>
						<span class="cal-date tabular-nums" aria-hidden="true">{cell.date.getDate()}</span>
						{#if d}
							<a
								href={dayHref(d.day)}
								class="cal-reading"
								dir="auto"
								aria-label="{fmt.long.format(cell.date)}: {t('plans.day')} {d.day}, {dayTitle(d)}"
							>
								<span class="block text-micro text-muted">{t('plans.day')} {d.day}</span>
								<span class="cal-title line-clamp-2 text-micro max-sm:hidden">{dayTitle(d)}</span>
							</a>
						{/if}
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
							<span class="shrink-0 tabular-nums text-muted">{ms.range ?? '✓'}</span>
						</li>
					{/each}
				</ul>
			{/if}
			{#if schedule.length}
				<!-- The schedule on the reader's own calendar: one event a reading,
				     each with an alert that morning — no account, no server. -->
				<label class="cal-field">
					<span class="text-eyebrow text-muted">{t('plans.remindAt')}</span>
					<input
						class="field"
						type="time"
						value={time}
						onchange={(e) => planSchedules.set(plan.slug, { time: e.currentTarget.value })}
					/>
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
		line-height: 1.35;
	}
	/* A phone's month: the date and the day number; titles are the list's. */
	@media (max-width: 639.98px) {
		.cal-cell {
			min-height: 3rem;
			padding: 0.25rem;
		}
	}
</style>
