<script lang="ts">
	import type { BookStage } from '$lib/series';

	/**
	 * A reader's place in a series as one segment per book — finished, being
	 * read, not begun — in reading order. The series card and the index's
	 * "Continue your series" rows draw it; the visible line beside it is the
	 * caller's, and `label` repeats it for assistive tech. `weights` sizes each
	 * segment by its share (a book page's chapters by length); equal without.
	 */
	let { stages, label, weights }: { stages: BookStage[]; label: string; weights?: number[] } = $props();
	const done = $derived(stages.filter((s) => s === 'done').length);
</script>

<div
	class="segments"
	role="progressbar"
	aria-label={label}
	aria-valuenow={done}
	aria-valuemin={0}
	aria-valuemax={stages.length}
>
	{#each stages as stage, i (i)}
		<span class="segment stage-mark {stage}" style:flex-grow={weights?.[i] || undefined}></span>
	{/each}
</div>

<style>
	.segments {
		display: flex;
		gap: 0.25rem;
	}
	.segment {
		flex: 1 1 0;
		/* Weighted, a short part (a preface) still shows. */
		min-width: 0.375rem;
		height: 0.3rem;
		border-radius: 9999px;
	}
</style>
