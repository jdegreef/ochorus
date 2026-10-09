<script lang="ts" module>
	import type { SealId, SealState } from '$lib/seals';

	/** Each seal's wax (app.css, --wax-*) and the emblem struck in it. */
	export const SEAL_WAX: Record<SealId, string> = {
		first: 'var(--wax-oxblood)',
		five: 'var(--wax-umber)',
		year: 'var(--wax-indigo)',
		hearer: 'var(--wax-ochre)',
		pupil: 'var(--wax-teal)',
		pilgrim: 'var(--wax-cypress)',
		margins: 'var(--wax-plum)',
		week: 'var(--wax-ember)',
		thirty: 'var(--wax-rust)',
		hundred: 'var(--wax-bronze)',
		centuries: 'var(--wax-violet)',
		tongues: 'var(--wax-pine)'
	};

	// The wax blob: a disc whose rim ripples where the wax spread under the
	// seal (sixteen lobes and a slow wobble, generated once).
	const BLOB =
		'M90.7 50.0 92.4 52.1 93.0 54.2 92.0 56.2 90.0 58.0 87.9 59.5 86.7 61.1 86.7 63.1 87.6 65.6 88.2 68.1 87.8 70.2 86.1 71.6 83.5 72.4 80.9 72.9 79.1 73.9 78.3 75.7 78.2 78.2 77.8 80.7 76.7 82.5 74.5 83.1 71.9 82.8 69.4 82.3 67.4 82.5 66.1 83.9 65.0 86.2 63.8 88.5 62.1 89.8 59.9 89.7 57.7 88.5 55.5 87.2 53.6 86.8 51.9 87.7 50.0 89.6 48.0 91.3 45.9 92.0 43.9 91.1 42.2 89.2 40.7 87.3 39.0 86.2 37.0 86.4 34.5 87.4 31.9 88.2 29.7 87.9 28.2 86.4 27.4 83.9 26.7 81.4 25.6 79.7 23.7 79.0 21.2 78.8 18.6 78.5 16.7 77.3 16.0 75.2 16.3 72.5 16.7 69.9 16.5 67.9 15.1 66.5 12.9 65.4 10.7 64.1 9.5 62.3 9.8 60.1 11.1 57.7 12.5 55.6 13.1 53.6 12.3 51.8 10.7 50.0 9.1 48.0 8.6 45.9 9.5 44.0 11.6 42.4 13.6 40.9 14.7 39.3 14.6 37.3 13.7 34.9 12.8 32.4 13.0 30.2 14.6 28.8 17.0 27.9 19.4 27.3 21.0 26.2 21.6 24.2 21.6 21.6 21.8 18.9 22.9 16.9 24.9 16.1 27.5 16.3 30.0 16.6 31.9 16.2 33.3 14.7 34.4 12.3 35.7 10.0 37.5 8.7 39.7 8.8 42.1 10.0 44.3 11.4 46.3 12.0 48.1 11.2 50.0 9.6 52.1 8.0 54.2 7.6 56.1 8.7 57.8 10.8 59.3 13.0 60.8 14.3 62.8 14.3 65.1 13.5 67.6 12.8 69.7 13.2 71.1 14.8 71.8 17.4 72.4 19.9 73.3 21.6 75.2 22.2 77.7 22.3 80.3 22.5 82.2 23.5 83.0 25.5 82.8 28.1 82.5 30.5 82.8 32.4 84.4 33.7 86.8 34.7 89.2 36.0 90.7 37.7 90.6 39.8 89.5 42.1 88.3 44.3 87.9 46.3 88.9 48.1 90.7 50.0Z';
</script>

<script lang="ts">
	/**
	 * A reading seal as wax: pressed and coloured when earned (a lit rim, a
	 * shine, the emblem struck in --wax-ink), an unpressed blank with a dashed
	 * rim while on the way, and a plain grey blank before. Decoration — every
	 * caller names the seal beside it — so it is hidden from assistive tech.
	 * The emblems are symmetric or read either way: nothing mirrors in RTL.
	 */
	let { id, state, size = '4.5rem' }: { id: SealId; state: SealState; size?: string } = $props();
	const earned = $derived(state === 'earned');
</script>

<svg
	class="seal-mark"
	class:earned
	class:progress={state === 'progress'}
	viewBox="0 0 100 100"
	style:width={size}
	style:height={size}
	style:--wax={SEAL_WAX[id]}
	aria-hidden="true"
	focusable="false"
>
	<path class="wax" d={BLOB} />
	{#if earned}
		<circle class="rim-lit" cx="50" cy="50" r="31" />
		<circle class="rim-shade" cx="50" cy="50" r="27" />
		<ellipse class="shine" cx="38" cy="32" rx="16" ry="9" transform="rotate(-25 38 32)" />
	{/if}
	<g class="emblem" transform="translate(50 50) scale(1.15)">
		{#if id === 'first'}
			<path d="M-14 -8c5-2 9-2 14 1 5-3 9-3 14-1v20c-5-2-9-2-14 1-5-3-9-3-14-1zM0 -7v21" />
		{:else if id === 'five'}
			<path d="M-15 12h30M-11 12V-8h5v20M-4 12V-11h6v23M5 12l6-19 4 1-5 18" />
		{:else if id === 'year'}
			<rect x="-13" y="-10" width="26" height="23" rx="2" />
			<path d="M-13 -3h26M-7 -14v7M7 -14v7M-6 4l4 4 8-9" />
		{:else if id === 'hearer'}
			<rect x="-4" y="-14" width="8" height="16" rx="4" />
			<path d="M-10 -2a10 10 0 0 0 20 0M0 8v6M-5 14h10" />
		{:else if id === 'pupil'}
			<path d="M0 15V-3M0 -3c-6-1-9-7-8-13 5 2 8 7 8 13zM0 -3c6-1 9-7 8-13-5 2-8 7-8 13zM0 6c-5 0-8-3-9-8 5 0 8 3 9 8zM0 6c5 0 8-3 9-8-5 0-8 3-9 8z" />
		{:else if id === 'pilgrim'}
			<path class="dotted" d="M-13 13c6-3 8-8 12-12s9-7 14-8" />
			<circle cx="-12" cy="12" r="2.5" />
			<path d="M8 -1v-13M8 -12h9l2 2-2 2H8" />
		{:else if id === 'margins'}
			<path d="M13 -14C3 -10-6 -1-10 12l3 1C-2 2 6-6 13-14zM-10 12l-2 4M-5 2l5 2" />
		{:else if id === 'week'}
			<path d="M0 -15c4 8 11 11 11 19a11 11 0 0 1-22 0c0-5 3-8 6-11 0 4 2 6 4 6-1-5 0-10 1-14z" />
		{:else if id === 'thirty'}
			<circle r="6" />
			<path d="M0 -15v4M0 11v4M-15 0h4M11 0h4M-10 -10l3 3M7 7l3 3M-10 10l3-3M7 -7l3-3" />
		{:else if id === 'hundred'}
			<path d="M-13 8l-2-16 8 7 7-11 7 11 8-7-2 16zM-13 12h26" />
		{:else if id === 'centuries'}
			<path d="M-10 -12h18a4 4 0 0 1 0 8H-6v18a4 4 0 0 1-8 0V-8a4 4 0 0 1 4-4zM-2 0h8M-2 6h8" />
		{:else}
			<path d="M-12 -10h12v9h-7l-5 4zM12 -2H2v9h6l4 4z" />
		{/if}
	</g>
</svg>

<style>
	.seal-mark {
		display: block;
		flex: none;
		overflow: visible;
	}
	.wax {
		fill: var(--surface-2);
		stroke: var(--border-strong);
		stroke-width: 1.2;
	}
	.progress .wax {
		stroke-dasharray: 3 4;
	}
	.earned .wax {
		fill: var(--wax);
		stroke: rgb(0 0 0 / 0.25);
		filter: drop-shadow(0 3px 4px rgb(0 0 0 / 0.35));
	}
	.rim-lit {
		fill: none;
		stroke: rgb(255 240 210 / 0.35);
		stroke-width: 1.6;
	}
	.rim-shade {
		fill: none;
		stroke: rgb(0 0 0 / 0.25);
	}
	.shine {
		fill: rgb(255 255 255 / 0.14);
	}
	.emblem {
		fill: none;
		stroke: var(--muted);
		stroke-width: 1.9;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.earned .emblem {
		stroke: var(--wax-ink);
	}
	.dotted {
		stroke-dasharray: 2 4;
	}
	@media print {
		.earned .wax {
			filter: none;
		}
	}
</style>
