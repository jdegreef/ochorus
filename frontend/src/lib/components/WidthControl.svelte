<script lang="ts">
	import { readerPrefs, MEASURE, type Measure } from '$lib/readerPrefs.svelte';

	// Narrower / wider stepper for the reading column, mirroring Take Root's
	// WidthControl. Steps the reader's measure preference (narrow ⇄ normal ⇄ wide).
	const ORDER = Object.keys(MEASURE) as Measure[];

	const idx = $derived(ORDER.indexOf(readerPrefs.measure));
	const atMin = $derived(idx <= 0);
	const atMax = $derived(idx >= ORDER.length - 1);

	function step(delta: number) {
		const next = ORDER[Math.min(ORDER.length - 1, Math.max(0, idx + delta))];
		readerPrefs.setMeasure(next);
	}
</script>

<div class="widthctl">
	<button type="button" onclick={() => step(-1)} disabled={atMin} aria-label="Narrower">
		<svg width="18" height="14" viewBox="0 0 24 18" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="4 4 8 9 4 14" /><polyline points="20 4 16 9 20 14" /><line x1="8" y1="9" x2="16" y2="9" /></svg>
	</button>
	<button type="button" onclick={() => step(1)} disabled={atMax} aria-label="Wider">
		<svg width="18" height="14" viewBox="0 0 24 18" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="8 4 4 9 8 14" /><polyline points="16 4 20 9 16 14" /><line x1="4" y1="9" x2="20" y2="9" /></svg>
	</button>
</div>
