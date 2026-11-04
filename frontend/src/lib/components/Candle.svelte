<script lang="ts">
	import { FLAME_PATH } from '$lib/flamePath';

	/**
	 * A small lit taper — the birthday candle that burns by a writer's name on
	 * their day (AuthorCandle, OnThisDay). The flame is the streak flame's and
	 * the reading lamps' (FLAME_PATH), the wax the lamps' gold. Decorative: the
	 * words beside it say whose day it is. The flame catches once as it
	 * appears, then burns still.
	 */
</script>

<svg class="candle" viewBox="0 0 16 32" aria-hidden="true" focusable="false">
	<g transform="translate(-1 -1) scale(0.75)"><path class="flame" d={FLAME_PATH} /></g>
	<path class="wick" d="M8 10.4v3.6" />
	<rect class="wax" x="5" y="14" width="6" height="17" rx="1.2" />
</svg>

<style>
	.candle {
		display: inline-block;
		width: 0.75em;
		height: 1.5em;
		flex: none;
		overflow: visible;
		vertical-align: -0.3em;
	}
	.wax {
		fill: var(--gold);
	}
	.wick {
		stroke: currentColor;
		stroke-width: 1;
		stroke-linecap: round;
		opacity: 0.7;
	}
	/* Fire is light in every theme: the theme's gold, lifted toward white (as
	   the reading lamps burn). */
	.flame {
		fill: color-mix(in srgb, var(--gold) 40%, white);
		stroke: color-mix(in srgb, var(--gold) 85%, transparent);
		stroke-width: 1.2;
		transform-box: fill-box;
		transform-origin: 50% 100%;
	}
	@media (prefers-reduced-motion: no-preference) {
		.flame {
			animation: candle-catch 900ms cubic-bezier(0.2, 0.7, 0.3, 1) 0.3s backwards;
		}
	}
	@keyframes candle-catch {
		from {
			opacity: 0;
			scale: 0.3;
		}
		60% {
			opacity: 1;
			scale: 1.15;
		}
	}
</style>
