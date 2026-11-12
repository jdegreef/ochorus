<script lang="ts">
	import type { JourneyLandmark, JourneyMapConfig } from '$lib/journeyMaps';
	import { MAP_HEIGHT, MAP_WIDTH } from '$lib/journeyMaps';
	import { journeyStates, roadPath, type ReaderPlace } from '$lib/journeyMap';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * An allegory's road, drawn: each place a stop, each stop a link to the
	 * chapter where it happens, and the reader's own way along it — the places
	 * passed in the accent, a ring where they are now. The place comes from
	 * this device's reading position (the book page passes it), so the
	 * prerendered page and a first visit draw the road with nothing passed.
	 *
	 * ONE set of links: the list under the picture, which is what a keyboard
	 * and a screen reader use. The picture repeats the stops for a pointer
	 * (tabindex -1, hidden from assistive tech) — the same links twice in the
	 * tab order would be noise. Names on the picture show from `sm`; on a phone
	 * the picture's numbers key into the list.
	 */
	let {
		map,
		place,
		chapterHref,
		lang
	}: {
		map: JourneyMapConfig;
		place: ReaderPlace;
		/** A chapter's reader URL, in the edition the page reads. */
		chapterHref: (order: number) => string;
		/** The map's language (its place names are the book's words). */
		lang: string;
	} = $props();

	const t = i18n.t;
	const states = $derived(journeyStates(map.stops, place));
	const hereIndex = $derived(states.indexOf('here'));
	const passedCount = $derived(states.filter((s) => s === 'passed').length);
	const road = $derived(roadPath(map.stops));
	// The road behind the reader: through every stop up to where they are.
	const walked = $derived.by(() => {
		const upTo = hereIndex >= 0 ? hereIndex : passedCount - 1;
		return upTo > 0 ? roadPath(map.stops.slice(0, upTo + 1)) : '';
	});
	const status = $derived(
		hereIndex >= 0
			? `${t('journey.youAreHere')}: ${map.stops[hereIndex].name}`
			: t('journey.passed').replace('%n%', String(passedCount)).replace('%t%', String(map.stops.length))
	);

	// Label offsets per side: above/below centred, start/end beside the dot.
	const LABEL = {
		above: { dx: 0, dy: -13, anchor: 'middle' },
		below: { dx: 0, dy: 21, anchor: 'middle' },
		start: { dx: -12, dy: 4, anchor: 'end' },
		end: { dx: 12, dy: 4, anchor: 'start' }
	} as const;

	const hills = (l: Extract<JourneyLandmark, { kind: 'hills' }>) => {
		const s = l.scale ?? 1;
		const p = (dx: number, dy: number) => `${l.x + dx * s},${l.y + dy * s}`;
		return `M${p(-34, 14)} L${p(-16, -12)} L${p(-4, 2)} L${p(10, -20)} L${p(34, 14)}`;
	};
</script>

<div class="journey" {lang}>
	<p class="mb-3 text-small text-muted">
		{map.scope}{#if place.current != null || place.finished}<span class="sep" aria-hidden="true">{' · '}</span><span
				class="font-semibold text-text">{status}</span
			>{/if}
	</p>

	<svg
		class="journey-map"
		viewBox="0 0 {MAP_WIDTH} {MAP_HEIGHT}"
		aria-hidden="true"
		focusable="false"
		preserveAspectRatio="xMidYMid meet"
	>
		<!-- The land: two soft washes, the far country lighter. -->
		<path class="land" d="M0,360 L0,250 C90,210 170,268 260,236 S420,250 500,214 S640,180 720,150 L720,360 Z" />
		<path class="land far" d="M0,190 C120,160 210,180 300,140 S470,110 560,70 S680,20 720,10 L720,0 L0,0 Z" />

		{#each map.landmarks as l, i (i)}
			{#if l.kind === 'hills'}
				<path class="mark-line" d={hills(l)} />
			{:else if l.kind === 'slough'}
				<ellipse class="slough" cx={l.x} cy={l.y} rx="26" ry="9" />
			{:else if l.kind === 'cross'}
				<path class="mark-line strong" d="M{l.x},{l.y - 14} V{l.y + 8} M{l.x - 7},{l.y - 7} H{l.x + 7}" />
			{:else if l.kind === 'castle'}
				<path
					class="mark-line"
					d="M{l.x - 12},{l.y + 10} V{l.y - 6} h4 v-4 h4 v4 h8 v-4 h4 v4 h4 V{l.y + 10} Z M{l.x - 2},{l.y + 10} v-7 h4 v7"
				/>
			{:else if l.kind === 'river'}
				<path class="river" d={l.d} />
			{:else if l.kind === 'city'}
				<g class="city">
					<circle class="glow" cx={l.x} cy={l.y} r="30" />
					{#each [0, 45, 90, 135, 180, 225, 270, 315] as a (a)}
						<line
							class="ray"
							x1={l.x + 16 * Math.cos((a * Math.PI) / 180)}
							y1={l.y + 16 * Math.sin((a * Math.PI) / 180)}
							x2={l.x + 26 * Math.cos((a * Math.PI) / 180)}
							y2={l.y + 26 * Math.sin((a * Math.PI) / 180)}
						/>
					{/each}
				</g>
			{/if}
		{/each}

		<path class="road" d={road} />
		{#if walked}<path class="road walked" d={walked} />{/if}

		{#each map.stops as stop, i (stop.name)}
			{@const state = states[i]}
			{@const lab = LABEL[stop.label]}
			<a href={chapterHref(stop.chapter)} tabindex="-1" class="stop {state}">
				{#if state === 'here'}<circle class="here-ring" cx={stop.x} cy={stop.y} r="15" />{/if}
				<circle class="dot" cx={stop.x} cy={stop.y} r={state === 'here' ? 10 : 8.5} />
				<text class="num" x={stop.x} y={stop.y + 3.4} text-anchor="middle">{i + 1}</text>
				<text class="name" x={stop.x + lab.dx} y={stop.y + lab.dy} text-anchor={lab.anchor}>{stop.name}</text>
			</a>
		{/each}
	</svg>

	<!-- The stops as a list: the links, for every reader. -->
	<ol class="journey-list mt-4">
		{#each map.stops as stop, i (stop.name)}
			{@const state = states[i]}
			<li>
				<a
					href={chapterHref(stop.chapter)}
					class="journey-row {state}"
					aria-current={state === 'here' ? 'location' : undefined}
				>
					<span class="journey-num" aria-hidden="true">{i + 1}</span>
					<span class="min-w-0 flex-1">{stop.name}</span>
					<span class="text-micro text-muted whitespace-nowrap">
						{#if state === 'here'}<span class="font-semibold text-accent">{t('journey.youAreHere')}</span>{' · '}{:else if state === 'passed'}<span class="sr-only">{t('settings.heatmapRead')}, </span>{/if}{t(
							'continue.chapter'
						)}
						{stop.chapter}
					</span>
				</a>
			</li>
		{/each}
	</ol>
</div>

<style>
	.journey-map {
		display: block;
		width: 100%;
		max-width: 48rem;
		height: auto;
		border-radius: var(--radius-card);
		background: var(--surface);
		box-shadow: inset 0 0 0 1px var(--border);
	}
	.land {
		fill: var(--surface-2);
	}
	.land.far {
		fill: var(--surface-2);
		opacity: 0.45;
	}
	.mark-line {
		fill: none;
		stroke: var(--border-strong);
		stroke-width: 1.5;
		stroke-linejoin: round;
		stroke-linecap: round;
	}
	.mark-line.strong {
		stroke-width: 2.5;
	}
	.slough {
		fill: var(--border);
		stroke: var(--border-strong);
		stroke-width: 1;
		stroke-dasharray: 2 3;
	}
	.river {
		fill: none;
		stroke: var(--accent-soft-border);
		stroke-width: 7;
		stroke-linecap: round;
	}
	.city .glow {
		fill: var(--gold);
		opacity: 0.16;
	}
	.city .ray {
		stroke: var(--gold);
		stroke-width: 2;
		stroke-linecap: round;
		opacity: 0.8;
	}
	.road {
		fill: none;
		stroke: var(--border-strong);
		stroke-width: 2.5;
		stroke-dasharray: 1 7;
		stroke-linecap: round;
	}
	.road.walked {
		stroke: var(--accent);
		stroke-width: 3.5;
		stroke-dasharray: none;
	}
	.stop .dot {
		fill: var(--surface);
		stroke: var(--border-strong);
		stroke-width: 1.5;
	}
	.stop.passed .dot {
		fill: var(--accent);
		stroke: var(--accent);
	}
	.stop.here .dot {
		fill: var(--surface);
		stroke: var(--accent);
		stroke-width: 3;
	}
	.here-ring {
		fill: none;
		stroke: var(--accent);
		stroke-width: 1.5;
		opacity: 0.5;
		transform-box: fill-box;
		transform-origin: center;
		animation: here-pulse 2.4s ease-in-out infinite;
	}
	@keyframes here-pulse {
		50% {
			transform: scale(1.25);
			opacity: 0.15;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.here-ring {
			animation: none;
		}
	}
	.stop .num {
		font: 600 9px var(--font-sans);
		fill: var(--muted);
	}
	.stop.passed .num {
		fill: var(--accent-contrast);
	}
	.stop.here .num {
		fill: var(--accent);
	}
	.stop .name {
		display: none;
		font: 500 11.5px var(--font-sans);
		fill: var(--text);
		paint-order: stroke;
		stroke: var(--surface);
		stroke-width: 3px;
		stroke-linejoin: round;
	}
	.stop.ahead .name {
		fill: var(--muted);
	}
	.stop:hover .dot {
		stroke: var(--accent);
	}
	@media (min-width: 640px) {
		.stop .name {
			display: inline;
		}
	}

	.journey-list {
		display: grid;
		gap: 0 1.5rem;
		max-width: 48rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	@media (min-width: 640px) {
		.journey-list {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	.journey-row {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		padding: 0.35rem 0.5rem;
		border-radius: var(--radius-sm);
		font-size: var(--fs-small);
		color: var(--text);
		text-decoration: none;
	}
	.journey-row:hover {
		background: var(--surface-2);
		text-decoration: none;
	}
	.journey-row.here {
		background: var(--accent-soft);
	}
	.journey-num {
		display: inline-flex;
		flex-shrink: 0;
		align-items: center;
		justify-content: center;
		width: 1.35rem;
		height: 1.35rem;
		border: 1.5px solid var(--border-strong);
		border-radius: 50%;
		font-size: var(--fs-micro);
		font-variant-numeric: tabular-nums;
		color: var(--muted);
	}
	.journey-row.passed .journey-num {
		border-color: var(--accent);
		background: var(--accent);
		color: var(--accent-contrast);
	}
	.journey-row.here .journey-num {
		border: 2px solid var(--accent);
		color: var(--accent);
		font-weight: 600;
	}
</style>
