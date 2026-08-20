<script lang="ts">
	/**
	 * How far through something you are — one meter, five callers.
	 *
	 * The same two nested divs were written out in Continue reading, Your plans,
	 * the plan page and twice on the plans shelf, at three different heights and
	 * on two different tracks (`bg-surface-2` on four of them, `bg-surface` on
	 * the fifth, which sat on a surface-2 card and so had almost no track at
	 * all). None of the five told a screen reader anything: they were bare divs
	 * with an inline width, so a reader who could not see the bar had no way to
	 * learn they were 40% through a plan.
	 *
	 * `role="progressbar"` with the value on it fixes that, and `aria-label`
	 * is required rather than optional because "40%" with no subject is not an
	 * improvement over silence.
	 *
	 * Note the fifth caller: its track was `bg-surface` because its card is
	 * `bg-surface-2` — the kind of per-site correction that stops happening once
	 * there is one component, so the track here is translucent instead.
	 */
	let {
		percent,
		label,
		size = 'sm'
	}: {
		/** 0–100. Clamped, so a caller's rounding can't paint outside the track. */
		percent: number;
		/** What is being measured, e.g. "Thirty Days in the Psalms: reading progress". */
		label: string;
		/** `sm` on a card, `md` where the meter is the point of the block. */
		size?: 'sm' | 'md';
	} = $props();

	const pct = $derived(Math.max(0, Math.min(100, Math.round(percent))));
</script>

<div
	class="track {size}"
	role="progressbar"
	aria-label={label}
	aria-valuenow={pct}
	aria-valuemin={0}
	aria-valuemax={100}
>
	<div class="fill" style="width: {pct}%"></div>
</div>

<style>
	.track {
		overflow: hidden;
		border-radius: 9999px;
		/* Translucent, not a named surface: these meters sit on `surface` in some
		   cards and on `surface-2` in others, and the one that hardcoded
		   `bg-surface-2` on a surface-2 card had effectively no track at all. A
		   tint of the text colour reads on any of them, in all three themes. */
		background: color-mix(in srgb, var(--text) 14%, transparent);
	}
	.sm {
		height: 0.375rem;
	}
	.md {
		height: 0.5rem;
	}
	.fill {
		height: 100%;
		border-radius: 9999px;
		background: var(--accent);
	}
	/* Only `md` animates. `width` is a layout property, so a shelf of twenty
	   small bars changing together would be twenty layout passes a frame; the
	   one bar that actually moves under the reader's eye — the plan page's, when
	   a day is marked done — is the `md` one. */
	@media (prefers-reduced-motion: no-preference) {
		.md .fill {
			transition: width var(--duration-slow);
		}
	}
</style>
