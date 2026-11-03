<script lang="ts">
	import type { Feast } from '$lib/liturgical';
	import { skyBody } from '$lib/prayerHours';

	/**
	 * The home hero's heavens at the reader's hour (HomeHero passes its `now`):
	 * the sun on its arc by day, a crescent moon among stars by night. Over
	 * the scrim, under the greeting; decoration only. The hour's colour itself
	 * is washed in under the scrim, by HomeHero.
	 *
	 * On Christmas Day and Easter morning the feast's own light (HeroFeast) —
	 * the star, the sunrise — takes the sun's or moon's place; the night's
	 * stars stay.
	 */
	let { now, feast }: { now: Date; feast: Feast | null } = $props();
	const sky = $derived(skyBody(now));
	const feastLit = $derived(feast === 'christmas' || feast === 'easter');
</script>

<div class="heavens" class:night={sky.body === 'moon'} aria-hidden="true">
	{#if !feastLit}
		<span class={sky.body} style:--along={sky.along.toFixed(3)} style:--height={sky.height.toFixed(3)}></span>
	{/if}
</div>

<style>
	/* Only the band's top. The body's lowest edge (--horizon + --size) stays
	   above the date line, which starts at the column's pt-9 (2.25rem) on a
	   phone and pt-11 (2.75rem) wider; the arc keeps to the inline start of
	   the frame. */
	.heavens {
		position: absolute;
		inset: 0 0 auto;
		height: 9rem;
		pointer-events: none;
	}
	.night {
		background-image:
			radial-gradient(1px 1px at 14% 14%, white, transparent),
			radial-gradient(1px 1px at 31% 7%, white, transparent),
			radial-gradient(1.4px 1.4px at 47% 18%, white, transparent),
			radial-gradient(1px 1px at 63% 9%, white, transparent),
			radial-gradient(1px 1px at 76% 21%, white, transparent),
			radial-gradient(1.4px 1.4px at 88% 6%, white, transparent),
			radial-gradient(1px 1px at 22% 26%, white, transparent),
			radial-gradient(1px 1px at 55% 4%, white, transparent);
	}
	.sun,
	.moon {
		--size: 0.9rem;
		--horizon: 1.2rem;
		--rise: 0.95rem;
		position: absolute;
		width: var(--size);
		height: var(--size);
		border-radius: 50%;
		inset-inline-start: calc(6% + var(--along) * 70%);
		top: calc(var(--horizon) - var(--height) * var(--rise));
	}
	@media (min-width: 640px) {
		.sun,
		.moon {
			--size: 1.05rem;
			--horizon: 1.5rem;
			--rise: 1.2rem;
		}
	}
	.sun {
		background: color-mix(in srgb, var(--season-white) 55%, var(--hero-gilt));
		box-shadow:
			0 0 10px 2px color-mix(in srgb, var(--hero-gilt) 70%, transparent),
			0 0 32px 10px color-mix(in srgb, var(--hero-gilt) 25%, transparent);
	}
	/* A crescent: the full disc with a bite masked out of its far side. */
	.moon {
		background: var(--season-white);
		-webkit-mask-image: radial-gradient(circle at 72% 32%, transparent 42%, black 44%);
		mask-image: radial-gradient(circle at 72% 32%, transparent 42%, black 44%);
	}
</style>
