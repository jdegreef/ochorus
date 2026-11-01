<script lang="ts">
	import { untrack } from 'svelte';

	/**
	 * A reading plan's progress as a garden: a plant for every day, in the
	 * plan's own hue (PLAN_META). A day read is in flower, today's reading is a
	 * sprout, the days ahead are seeds in the ground. A day skipped stays a
	 * seed — the garden never shows anything dead or a mark against the reader.
	 *
	 * A long plan shows the stretch around today (WINDOW days) rather than a
	 * row of plants too small to see; the label still counts the whole plan.
	 *
	 * A day marked read while the garden is on screen grows into flower (stem,
	 * leaves, then the bloom) and the next day's sprout comes up after it; the
	 * garden as it was on arrival is simply drawn, so a visit never replays.
	 *
	 * One image to assistive tech: `label` says the progress in words ("Humility
	 * in 12 Days: 4 of 12 days"), the drawing is decoration. The row runs in
	 * reading order, so it reverses in a right-to-left locale with the text.
	 */
	let {
		dayCount,
		done,
		next,
		hue,
		label
	}: {
		dayCount: number;
		/** The days marked read. */
		done: Set<number>;
		/** Today's reading, or null once every day is read. */
		next: number | null;
		/** The plan's accent (planMeta). */
		hue: string;
		label: string;
	} = $props();

	const WINDOW = 21;

	const days = $derived.by(() => {
		if (dayCount <= WINDOW) return Array.from({ length: dayCount }, (_, i) => i + 1);
		// Today a third of the way in, so more of the road ahead shows than behind.
		const anchor = next ?? dayCount;
		const first = Math.min(Math.max(1, anchor - Math.floor(WINDOW / 3)), dayCount - WINDOW + 1);
		return Array.from({ length: WINDOW }, (_, i) => first + i);
	});

	const stateOf = (d: number): 'flower' | 'sprout' | 'seed' =>
		done.has(d) ? 'flower' : d === next ? 'sprout' : 'seed';

	// The garden as it stood when it was drawn: anything that changes after
	// that happened in front of the reader, and grows in.
	const arrived = untrack(() => ({ done: new Set(done), next }));
	const grows = (d: number, s: 'flower' | 'sprout' | 'seed') =>
		s === 'flower' ? !arrived.done.has(d) : s === 'sprout' && d !== arrived.next;
</script>

<div class="garden" role="img" aria-label={label} style:--plan-hue={hue}>
	{#each days as d (d)}
		{@const s = stateOf(d)}
		<svg class="plant" class:today={s === 'sprout'} class:grow={grows(d, s)} viewBox="0 0 24 40" aria-hidden="true" focusable="false">
			{#if s === 'flower'}
				<path class="stem" d="M12 39V16" pathLength="1" />
				<path class="leaf" d="M12 30c-4 0-6.5-2.5-6.5-6 4 0 6.5 2.5 6.5 6zM12 26c4 0 6.5-2.5 6.5-6-4 0-6.5 2.5-6.5 6z" />
				<circle class="bloom" cx="12" cy="11" r="5" />
				<circle class="heart" cx="12" cy="11" r="2" />
			{:else if s === 'sprout'}
				<path class="stem" d="M12 39V28" pathLength="1" />
				<path class="leaf" d="M12 31c-3.5 0-5.5-2-5.5-5 3.5 0 5.5 2 5.5 5zM12 29c3.5 0 5.5-2 5.5-5-3.5 0-5.5 2-5.5 5z" />
			{:else}
				<ellipse class="seed" cx="12" cy="37.5" rx="2.2" ry="1.4" />
			{/if}
		</svg>
	{/each}
</div>

<style>
	.garden {
		display: flex;
		align-items: flex-end;
		gap: 2px;
		padding-bottom: 3px;
		/* The soil line the row stands on. */
		border-bottom: 2px solid color-mix(in srgb, var(--plan-hue) 35%, var(--border));
	}
	.plant {
		flex: 1 1 0;
		min-width: 0;
		max-width: 1.75rem;
		height: auto;
		aspect-ratio: 24 / 40;
		overflow: visible;
	}
	.stem {
		fill: none;
		stroke: var(--plan-hue);
		stroke-width: 2;
		stroke-linecap: round;
	}
	.leaf {
		fill: var(--plan-hue);
	}
	/* The flower in the ornament metal (gold; silver in the cool palettes),
	   so a finished day catches the eye the way the gilt does elsewhere. */
	.bloom {
		fill: var(--ornament);
	}
	.heart {
		fill: color-mix(in srgb, var(--ornament) 45%, black);
	}
	.seed {
		fill: var(--border-strong);
	}
	/* Today's sprout stands in a faint halo of the plan's hue. */
	.today {
		background: radial-gradient(
			circle at 50% 75%,
			color-mix(in srgb, var(--plan-hue) 28%, transparent),
			transparent 70%
		);
		border-radius: 999px;
	}
	/* Growing in: the stem draws up, the leaves open, then the bloom (and its
	   heart) opens. A sprout that comes up beside a new flower waits for it.
	   Every step fills backwards, so the resting frame is the plant as drawn;
	   opt-in under no-preference, as the global reduced-motion rule keeps
	   delays and would leave a gap where the plant blinks in late. */
	.leaf,
	.bloom,
	.heart {
		transform-box: fill-box;
	}
	.leaf {
		transform-origin: 50% 100%;
	}
	.bloom,
	.heart {
		transform-origin: center;
	}
	@media (prefers-reduced-motion: no-preference) {
		.grow .stem {
			stroke-dasharray: 1;
			animation: garden-stem 0.6s ease-out var(--grow-delay, 0s) backwards;
		}
		.grow .leaf {
			animation: garden-open 0.45s ease-out calc(var(--grow-delay, 0s) + 0.45s) backwards;
		}
		.grow .bloom {
			animation: garden-open 0.5s cubic-bezier(0.3, 1.6, 0.5, 1) calc(var(--grow-delay, 0s) + 0.8s) backwards;
		}
		.grow .heart {
			animation: garden-open 0.35s ease-out calc(var(--grow-delay, 0s) + 1.1s) backwards;
		}
		.today.grow {
			--grow-delay: 1.2s;
		}
	}
	@keyframes garden-stem {
		from {
			stroke-dashoffset: 1;
		}
	}
	@keyframes garden-open {
		from {
			transform: scale(0);
		}
	}
	@media print {
		.today {
			background: none;
		}
	}
</style>
