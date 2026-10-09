<script lang="ts" module>
	export type EmptyArtName = 'book' | 'notes' | 'shelf' | 'search' | 'failed' | 'language' | 'path';
</script>

<script lang="ts">
	/**
	 * A small engraving for an empty state: a fine line in the ornament metal
	 * (--ornament: gold, silver in the cool palettes), the register of the
	 * fleuron and the printer's ornaments, so "nothing here yet" reads as a
	 * designed page rather than a rendering failure.
	 *
	 *   book     — a lamp over an open book: nothing here yet (the default)
	 *   notes    — an open book and a quill: nothing written yet
	 *   shelf    — a bare shelf, one book leaning: nothing started yet
	 *   search   — a page under a lens: nothing matched
	 *   failed   — a candle just snuffed: it didn't load
	 *   language — a globe and a book: not in this language yet
	 *   path     — a dotted way to a signpost: no journey begun
	 *
	 * Decoration only — the message beside it says what's (not) here — so it is
	 * hidden from assistive tech. Every shape is symmetric or reads either way,
	 * so it needs no mirroring in a right-to-left locale.
	 */
	let { name = 'book', class: klass = '' }: { name?: EmptyArtName; class?: string } = $props();
</script>

<svg class="empty-art {klass}" viewBox="0 0 150 120" aria-hidden="true" focusable="false">
	{#if name === 'book'}
		<path class="fill" d="M75 14c-5 7-5 13 0 16 5-3 5-9 0-16z" />
		<path d="M69 30h12v7H69zM60 37h30l-4 30H64zM64 46h22M63 55h24M56 67h38v7H56z" />
		<path d="M25 86c16-6 33-6 50 0 17-6 34-6 50 0v20c-16-6-33-6-50 0-17-6-34-6-50 0zM75 86v20" />
		<path d="M38 92h22M38 98h18M90 92h22M90 98h18M50 22l-6-6M100 22l6-6M75 6V2" />
	{:else if name === 'notes'}
		<path d="M25 70c16-6 33-6 50 0 17-6 34-6 50 0v26c-16-6-33-6-50 0-17-6-34-6-50 0zM75 70v26" />
		<path d="M36 78h24M36 85h20M90 78h22" />
		<path class="fill" d="M120 14c-14 6-28 22-34 44l6 2c8-18 20-32 28-46z" />
		<path d="M86 58l-3 8 6-4M100 36l8 4" />
	{:else if name === 'shelf'}
		<path d="M14 92h122M14 98h122M20 98v10M130 98v10" />
		<path d="M30 92V60h6v32M36 92V56h8v36M46 92l14-34 6 3-13 31" />
		<path class="fill" d="M112 92V66c0-4 10-4 10 0v26z" />
		<path class="faint" d="M70 40l4 4M80 34v6M88 40l-4 4" />
	{:else if name === 'search'}
		<path d="M30 22h60v76H30zM40 40h40M40 48h34M40 56h38M40 64h26" />
		<circle class="fill" cx="98" cy="62" r="20" />
		<path d="M112 76l18 18M92 58l12 8M104 58l-12 8" />
	{:else if name === 'failed'}
		<path d="M66 52h18v46H66zM60 98h30M54 106h42M75 52v-6" />
		<path class="faint" d="M75 44c-4-6 4-10 0-16 4 4 6 8 2 12M80 30c3-4 1-8-2-12" />
		<path class="fill" d="M66 60c6 2 12 2 18 0" />
	{:else if name === 'language'}
		<circle cx="58" cy="56" r="34" />
		<path d="M24 56h68M58 22c-12 10-12 58 0 68M58 22c12 10 12 58 0 68M30 38h56M30 74h56" />
		<path class="ground" d="M88 74l30-8v34l-30 8z" />
		<path d="M118 66l18 6v34l-18-6M96 82l14-4M96 90l14-4" />
	{:else if name === 'path'}
		<path class="faint" d="M20 108c20-6 30-16 40-28s26-22 50-26" />
		<circle class="fill" cx="28" cy="104" r="4" />
		<path d="M104 54V20M104 24h28l6 6-6 6h-28zM104 40H80l-6 6 6 6h24M100 54h8" />
	{/if}
</svg>

<style>
	.empty-art {
		display: block;
		width: 7.5rem;
		height: 6rem;
		margin-inline: auto;
		fill: none;
		stroke: var(--ornament);
		stroke-width: 1.4;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.fill {
		fill: color-mix(in srgb, var(--ornament) 22%, transparent);
	}
	.faint {
		stroke-dasharray: 2 4;
	}
	/* A shape that must hide the line behind it takes the panel's own ground. */
	.ground {
		fill: var(--surface);
	}
</style>
