<script lang="ts" generics="T extends string">
	/**
	 * One labelled group of one-tap choices inside a FilterSheet — the sheet's
	 * version of a `<select>`: every option visible, wrapping as chips so no
	 * label truncates (touch sizing comes from the global .chip rule).
	 */
	let {
		label,
		showLabel = true,
		options,
		value,
		isActive = (v: T) => v === value,
		onselect
	}: {
		/** Names the group — shown above it, and its aria-label either way. */
		label: string;
		/** Hide the visible label when the options name themselves ("All lengths"). */
		showLabel?: boolean;
		options: { v: T; label: string; count?: number }[];
		value?: T;
		/** Overrides `value` for a multi-select group (several chips on at once,
		 *  `onselect` toggling each) — the biographies facets. */
		isActive?: (v: T) => boolean;
		onselect: (v: T) => void;
	} = $props();
</script>

<div class="sheet-group">
	{#if showLabel}<p class="sheet-label">{label}</p>{/if}
	<div class="sheet-choices" role="group" aria-label={label}>
		{#each options as o (o.v)}
			<button class="chip" class:active={isActive(o.v)} aria-pressed={isActive(o.v)} onclick={() => onselect(o.v)}
				>{o.label}{#if o.count !== undefined}<span class="count">{o.count}</span>{/if}</button
			>
		{/each}
	</div>
</div>

<style>
	.sheet-label {
		margin-bottom: 0.5rem;
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--muted);
	}
	.sheet-choices {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
</style>
