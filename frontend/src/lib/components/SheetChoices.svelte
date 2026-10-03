<script lang="ts" generics="T extends string">
	/**
	 * One labelled group of one-tap choices inside a FilterSheet — the sheet's
	 * version of a `<select>`: every option visible, wrapping as chips so no
	 * label truncates (touch sizing comes from the global .chip rule).
	 *
	 * Options may nest one level: a `strong` option heads a group and the
	 * `indent` options after it sit beneath it, indented behind a rule — the
	 * biographies Place facet's regions and their countries, which otherwise
	 * read as one flat cloud with nothing to say England is inside Britain.
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
		options: { v: T; label: string; count?: number; strong?: boolean; indent?: boolean }[];
		value?: T;
		/** Overrides `value` for a multi-select group (several chips on at once,
		 *  `onselect` toggling each) — the biographies facets. */
		isActive?: (v: T) => boolean;
		onselect: (v: T) => void;
	} = $props();

	type Opt = (typeof options)[number];
	/** Runs of options: a `strong` head with its `indent`ed children, or a run
	 *  of plain options. Flat lists come back as one run, rendered as before. */
	const runs = $derived.by(() => {
		const out: { head?: Opt; items: Opt[] }[] = [];
		for (const o of options) {
			const last = out.at(-1);
			if (o.strong) out.push({ head: o, items: [] });
			else if (o.indent && last?.head) last.items.push(o);
			else if (last && !last.head) last.items.push(o);
			else out.push({ items: [o] });
		}
		return out;
	});
</script>

{#snippet choice(o: Opt)}
	<button
		class="chip"
		class:font-semibold={o.strong}
		class:active={isActive(o.v)}
		aria-pressed={isActive(o.v)}
		onclick={() => onselect(o.v)}
		>{o.label}{#if o.count !== undefined}<span class="count">{o.count}</span>{/if}</button
	>
{/snippet}

<div class="sheet-group">
	{#if showLabel}<p class="sheet-label">{label}</p>{/if}
	<div class="sheet-runs" role="group" aria-label={label}>
		{#each runs as r, i (r.head?.v ?? `run-${i}`)}
			{#if r.head}
				<div class="sheet-nest">
					<div class="sheet-choices">{@render choice(r.head)}</div>
					{#if r.items.length}
						<div class="sheet-choices sheet-kids">
							{#each r.items as o (o.v)}{@render choice(o)}{/each}
						</div>
					{/if}
				</div>
			{:else}
				<div class="sheet-choices">
					{#each r.items as o (o.v)}{@render choice(o)}{/each}
				</div>
			{/if}
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
	.sheet-runs {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.sheet-choices {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
	.sheet-nest {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	/* A region's places: indented behind a rule, so they read as inside it. */
	.sheet-kids {
		margin-inline-start: 0.6rem;
		padding-inline-start: 0.75rem;
		border-inline-start: 2px solid var(--border);
	}
</style>
