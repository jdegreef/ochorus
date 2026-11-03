<script lang="ts">
	import { onMount } from 'svelte';
	import { FLAME_PATH } from '$lib/flamePath';
	import { feastDay } from '$lib/liturgical';

	/**
	 * Whit Sunday: three small tongues of fire over the header's logo ("there
	 * appeared unto them cloven tongues like as of fire", Acts 2:3) — on that
	 * one day, and nowhere else. Placed in the brand link, which is
	 * `position: relative` for it.
	 *
	 * Decided on mount, not at render: the prerendered SEO pages are built
	 * once, on the build's own day, and must not carry its feast into every
	 * other day. Re-checked when the tab comes back into view, as the hero's
	 * date and the Church-year palette are, so a tab left open across the day
	 * lights (and puts out) the flames with them. Decorative (aria-hidden);
	 * the flames flicker up once and then burn still.
	 */
	let on = $state(false);
	onMount(() => {
		const check = () => {
			if (document.visibilityState === 'visible') on = feastDay(new Date()) === 'pentecost';
		};
		check();
		document.addEventListener('visibilitychange', check);
		return () => document.removeEventListener('visibilitychange', check);
	});
</script>

{#if on}
	<svg class="flames" viewBox="0 0 48 24" aria-hidden="true">
		<g transform="translate(12 0)"><path class="mid" d={FLAME_PATH} /></g>
		<!-- The outer pair: one tongue, and its mirror about the middle. -->
		{#each ['', 'translate(48 0) scale(-1 1)'] as mirror (mirror)}
			<g transform={mirror}>
				<!-- tilt-ok: the outer tongues lean out from the middle one, as flames do. -->
				<g transform="translate(-1 3) rotate(-14 12 22) scale(0.85)"><path d={FLAME_PATH} /></g>
			</g>
		{/each}
	</svg>
{/if}

<style>
	/* Over the wordmark, in the clear space right of the quill. The lockup is
	   artwork and never mirrors, so neither does this spot. */
	.flames {
		position: absolute;
		left: 2.15rem; /* rtl-ok: placed on the unmirrored logo artwork */
		top: 0.1rem;
		width: 2rem;
		pointer-events: none;
		overflow: visible;
		/* On the svg, not its paths: WebKit draws no CSS filter on SVG children. */
		filter: drop-shadow(0 0 2px color-mix(in srgb, var(--accent) 45%, transparent));
	}
	path {
		/* Fire, not the gold of the streak flame: the gold run toward the
		   day's liturgical red. */
		fill: color-mix(in srgb, var(--gold) 55%, var(--season-red));
		transform-box: fill-box;
		transform-origin: 50% 100%;
	}
	@media (prefers-reduced-motion: no-preference) {
		path {
			animation: flames-up 900ms cubic-bezier(0.2, 0.7, 0.3, 1) 0.4s backwards;
		}
		.mid {
			animation-delay: 0.25s;
		}
	}
	@keyframes flames-up {
		from {
			opacity: 0;
			scale: 1 0.2;
		}
		60% {
			opacity: 1;
			scale: 1 1.15;
		}
	}
</style>
