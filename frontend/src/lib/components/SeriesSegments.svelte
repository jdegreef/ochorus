<script lang="ts">
	import type { BookStage } from '$lib/series';

	/**
	 * A reader's place in a series as one segment per book — finished, being
	 * read, not begun — in reading order. The series card and the index's
	 * "Continue your series" rows draw it; the visible line beside it is the
	 * caller's, and `label` repeats it for assistive tech.
	 */
	let { stages, label }: { stages: BookStage[]; label: string } = $props();
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
		<span class="segment {stage}"></span>
	{/each}
</div>

<style>
	.segments {
		display: flex;
		gap: 0.25rem;
	}
	.segment {
		flex: 1;
		height: 0.3rem;
		border-radius: 9999px;
		/* ProgressBar's track: a tint of the text colour shows on the card's
		   surface in every theme, where surface-2 all but vanished. */
		background: color-mix(in srgb, var(--text) 14%, transparent);
	}
	.segment.done {
		background: var(--accent);
	}
	.segment.reading {
		background: var(--gold);
	}
</style>
