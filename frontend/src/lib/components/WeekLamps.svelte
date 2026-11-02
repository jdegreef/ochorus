<script lang="ts">
	import { weekLamps } from '$lib/heatmap';

	/**
	 * This week as seven small oil lamps (the dashboard's reading panel, beside
	 * the goal line): a day read is lit, its flame a little taller the further
	 * into a run it is; today, not yet read, is trimmed and waiting; a day gone
	 * by unread simply rests, and the days ahead stand dark. Nothing is ever
	 * shown as broken or lost — a missed day is a lamp at rest, not a mark.
	 *
	 * One image to assistive tech (`label` says it in words); the lamps and the
	 * weekday initials are decoration. The row runs in reading order, so it
	 * reverses with the text in a right-to-left locale.
	 */
	let { days, today, locale, label }: { days: string[]; today: string; locale: string; label: string } = $props();

	const lamps = $derived(weekLamps(days, today));
	const initial = $derived.by(() => {
		const f = new Intl.DateTimeFormat(locale, { weekday: 'narrow', timeZone: 'UTC' });
		return (day: string) => f.format(new Date(`${day}T00:00:00Z`));
	});
	/** A run's flame: from 0.7 on its first day to full height a week in. */
	const flame = (run: number) => (0.7 + Math.min(run, 7) * 0.043).toFixed(2);
</script>

<div class="lamps" role="img" aria-label={label}>
	{#each lamps as lamp (lamp.day)}
		<div class="lamp" data-state={lamp.state} class:today={lamp.day === today}>
			<svg viewBox="0 0 24 36" aria-hidden="true" focusable="false">
				{#if lamp.state === 'lit'}
					<ellipse class="glow" cx="12" cy="12" rx="9" ry="10" />
					<path class="flame" style:--s={flame(lamp.run)} d="M12 3c3 4 5 7 5 10a5 5 0 0 1-10 0c0-3 2-6 5-10z" />
				{/if}
				<path class="wick" d="M12 17v4" />
				<path class="body" d="M3 25c0-3 4-4 9-4s9 1 9 4-4 5-9 5-9-2-9-5zM18 24l5-2v2l-4 2z" />
				<path class="foot" d="M8 30h8l1 3H7z" />
			</svg>
			<span class="day" aria-hidden="true">{initial(lamp.day)}</span>
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
	/* Today, not yet read: trimmed and ready — the wick stands up, the lamp in
	   full metal, a faint ring of the accent round it. */
	[data-state='waiting'] .wick {
		stroke: var(--text);
	}
	[data-state='waiting'] svg {
		filter: drop-shadow(0 0 3px color-mix(in srgb, var(--accent) 45%, transparent));
	}
	/* At rest (gone by unread) and ahead: the same lamp, quieter. */
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
	/* A lit flame flickers, very gently, for a few breaths after the panel
	   appears — then stands still, so an open tab isn't animating for hours. */
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
	@media print {
		.flame {
			animation: none;
		}
	}
</style>
