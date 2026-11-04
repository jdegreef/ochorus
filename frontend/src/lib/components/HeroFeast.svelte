<script lang="ts">
	import type { Feast } from '$lib/liturgical';

	/**
	 * The home hero on a great feast (HomeHero passes `feastDay(now)`): on
	 * Christmas Day a star over the band, on Easter morning the light of a
	 * sunrise. Pentecost's flames are on the header's logo (PentecostFlames).
	 * Laid over the scrim and grain, under the greeting; decoration only — the
	 * season line already names the day. Each comes in once, as the page
	 * opens, and then rests.
	 */
	let { feast }: { feast: Feast } = $props();
</script>

{#if feast === 'christmas'}
	<div class="star" aria-hidden="true"><span></span></div>
{:else if feast === 'easter'}
	<div class="dawn" aria-hidden="true"></div>
	<div class="sweep" aria-hidden="true"></div>
{/if}

<style>
	/* Christmas Day: the star, a four-pointed spark in the season's white with
	   a gilt glow, its rays fanning faintly down over the band. It comes out
	   once, as the page opens, and then simply shines (no endless twinkle:
	   the band already has one slow animation). */
	.star {
		position: absolute;
		top: 0;
		inset-inline-start: 58%;
		width: 18rem;
		height: 100%;
		margin-inline-start: -9rem;
		pointer-events: none;
		/* The rays fade as they fall, rather than striking the band's foot. */
		-webkit-mask-image: linear-gradient(to bottom, black 15%, transparent 80%);
		mask-image: linear-gradient(to bottom, black 15%, transparent 80%);
		background: conic-gradient(
			from 0deg at 50% 2.6rem,
			transparent 0 43%,
			color-mix(in srgb, var(--hero-gilt) 22%, transparent) 46.5%,
			transparent 49% 51%,
			color-mix(in srgb, var(--hero-gilt) 18%, transparent) 53.5%,
			transparent 57%
		);
	}
	/* The glow on a wrapper: a filter on the clipped spark (::before) is
	   clipped away with everything outside its points. */
	.star > span {
		position: absolute;
		top: 1.6rem;
		inset-inline-start: 50%;
		width: 2rem;
		height: 2rem;
		margin-inline-start: -1rem;
		filter: drop-shadow(0 0 5px var(--hero-gilt)) drop-shadow(0 0 12px var(--hero-gilt));
	}
	.star > span::before {
		content: '';
		display: block;
		height: 100%;
		background: var(--season-white);
		clip-path: polygon(50% 0, 58% 42%, 100% 50%, 58% 58%, 50% 100%, 42% 58%, 0 50%, 42% 42%);
	}
	/* On a phone the date line runs nearly the band's width: the star moves up
	   into the margin above it, smaller, toward the inline end. */
	@media (max-width: 639px) {
		.star {
			inset-inline-start: 82%;
		}
		.star > span {
			top: 0.3rem;
			width: 1.4rem;
			height: 1.4rem;
			margin-inline-start: -0.7rem;
		}
	}
	/* Easter morning: the sky lightening along the top of the band — above
	   the date line, so the greeting keeps its contrast (the scrim, which
	   runs from the foot, would have hidden a sun rising there) — and once,
	   as the page opens, a band of sunlight passing over it. */
	.dawn,
	.sweep {
		position: absolute;
		inset: 0;
		pointer-events: none;
	}
	.dawn {
		background: radial-gradient(
			ellipse 60% 32% at 50% -8%,
			color-mix(in srgb, var(--season-white) 70%, transparent) 0%,
			color-mix(in srgb, var(--hero-gilt) 45%, transparent) 45%,
			transparent 100%
		);
	}
	.sweep {
		opacity: 0;
		background: linear-gradient(
			100deg,
			transparent 30%,
			color-mix(in srgb, var(--season-white) 30%, transparent) 48%,
			transparent 66%
		);
	}
	@media (prefers-reduced-motion: no-preference) {
		.star {
			animation: star-rays 2.4s ease-out 0.3s backwards;
		}
		.star > span {
			animation: star 1.6s cubic-bezier(0.2, 0.7, 0.3, 1) 0.3s backwards;
		}
		.dawn {
			animation: dawn 2.6s cubic-bezier(0.2, 0.6, 0.3, 1) 0.1s backwards;
		}
		.sweep {
			animation: sweep 2.8s ease-in-out 1s backwards;
		}
	}
	@keyframes star {
		from {
			opacity: 0;
			transform: scale(0.2);
		}
		60% {
			opacity: 1;
			transform: scale(1.25);
		}
	}
	@keyframes star-rays {
		from {
			opacity: 0;
		}
	}
	@keyframes dawn {
		from {
			opacity: 0;
			transform: translateY(-30%);
		}
	}
	/* The sweep alone rests invisible: a band of light passes, then is gone. */
	/* A right-to-left page reads, and so is lit, from the other side. */
	:global([dir='rtl']) .sweep {
		scale: -1 1;
	}
	@keyframes sweep {
		from {
			opacity: 1;
			transform: translateX(-100%);
		}
		to {
			opacity: 1;
			transform: translateX(100%);
		}
	}
</style>
