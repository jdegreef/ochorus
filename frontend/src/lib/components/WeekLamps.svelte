<script lang="ts">
	import { weekLamps } from '$lib/heatmap';

	/**
	 * This week as seven small oil lamps (the dashboard's reading panel, under
	 * the goal line): a day read is lit, its flame sized by the run's tier (the
	 * streak flame's and the calendar's), and the lamp that reached this week's
	 * goal wears a gold ring; today, not yet read, is trimmed and waiting; a day
	 * gone by unread simply rests; the days ahead stand dark. Nothing is shown
	 * as broken — a missed day is a lamp at rest, not a mark against the reader.
	 *
	 * One image to assistive tech (`label`, the goal line in words); the lamps
	 * and weekday initials are decoration. The row runs in reading order, so it
	 * reverses with the text in a right-to-left locale.
	 */
	let {
		days,
		today,
		goal,
		locale,
		label
	}: { days: string[]; today: string; goal: number; locale: string; label: string } = $props();

	const lamps = $derived(weekLamps(days, today));
	/** The lamp whose lighting met the goal: the goal-th lit one, if any. */
	const goalDay = $derived(lamps.filter((l) => l.state === 'lit')[goal - 1]?.day);
	const weekdays = $derived(new Intl.DateTimeFormat(locale, { weekday: 'narrow', timeZone: 'UTC' }));
	/** Flame height by tier: spark, flame, blaze, crown (Icon's flame is drawn
	 *  for a 24px icon; a lamp's wants it larger over the wick). */
	const FLAME = [0, 1, 1.12, 1.24, 1.36] as const;
</script>

<div class="lamps" role="img" aria-label={label}>
	{#each lamps as lamp (lamp.day)}
		<div class="lamp" data-state={lamp.state} class:today={lamp.day === today} class:goal={lamp.day === goalDay}>
			<svg viewBox="0 0 24 36" aria-hidden="true" focusable="false">
				{#if lamp.state === 'lit'}
					<ellipse class="glow" cx="12" cy="10" rx="9" ry="10" />
					<!-- Icon's flame, so it matches the streak flame beside it. -->
					<path
						class="flame"
						style:--s={FLAME[lamp.level]}
						d="M12 2c1.6 3.2 4.6 4.7 4.6 8.6a4.6 4.6 0 0 1-9.2 0c0-2 1-3.3 2.1-4.3.2 1.4 1 2.3 2 2.3 1.3 0 1.9-1.2 1.6-2.6C12.8 4.9 12 3.6 12 2z"
					/>
				{/if}
				<path class="wick" d="M12 15.5v5" />
				<path class="body" d="M3 25c0-3 4-4 9-4s9 1 9 4-4 5-9 5-9-2-9-5zM18 24l5-2v2l-4 2z" />
				<path class="foot" d="M8 30h8l1 3H7z" />
			</svg>
			<span class="day" aria-hidden="true">{weekdays.format(new Date(`${lamp.day}T00:00:00Z`))}</span>
		</div>
	{/each}
</div>

<style>
	.lamps {
		display: flex;
		gap: 0.35rem;
	}
	.lamp {
		display: grid;
		justify-items: center;
		gap: 0.15rem;
		flex: 1 1 0;
		max-width: 2.25rem;
		border-radius: 999px;
	}
	svg {
		width: 100%;
		max-width: 1.75rem;
		height: auto;
		overflow: visible;
	}
	.body,
	.foot {
		fill: var(--gold);
	}
	.wick {
		stroke: var(--muted);
		stroke-width: 1.4;
		stroke-linecap: round;
	}
	.flame {
		fill: color-mix(in srgb, var(--gold) 40%, white);
		stroke: color-mix(in srgb, var(--gold) 85%, transparent);
		stroke-width: 0.8;
		transform-box: fill-box;
		transform-origin: 50% 100%;
		transform: scale(var(--s));
	}
	.glow {
		fill: color-mix(in srgb, var(--gold) 28%, transparent);
	}
	/* The day the week's goal was met. */
	.goal {
		box-shadow: 0 0 0 1.5px var(--gold);
	}
	/* Today, unread: the wick stands up, a faint ring of the accent. */
	[data-state='waiting'] .wick {
		stroke: var(--text);
	}
	[data-state='waiting'] svg {
		filter: drop-shadow(0 0 3px color-mix(in srgb, var(--accent) 45%, transparent));
	}
	[data-state='rest'] svg {
		opacity: 0.55;
	}
	[data-state='ahead'] svg {
		opacity: 0.3;
	}
	.day {
		font-size: var(--fs-micro);
		line-height: 1;
		color: var(--muted);
	}
	.today .day {
		color: var(--text);
		font-weight: 600;
	}
	/* A few breaths of flicker as the panel appears, then still. */
	@media (prefers-reduced-motion: no-preference) {
		.flame {
			animation: lamp-flicker 1.8s ease-in-out 6 alternate;
		}
		.lamp:nth-child(even) .flame {
			animation-duration: 1.4s;
		}
	}
	@keyframes lamp-flicker {
		to {
			transform: scale(calc(var(--s) * 1.05), calc(var(--s) * 0.96));
		}
	}
</style>
