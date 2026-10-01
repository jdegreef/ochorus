<script lang="ts" module>
	/** One tick. `indent` nests an option under the `strong` one above it
	 *  (a place under its region). */
	export type FacetOption = {
		v: string;
		label: string;
		count: number;
		indent?: boolean;
		strong?: boolean;
	};
</script>

<script lang="ts">
	import { dismissable } from '$lib/actions/dismissable';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * A multi-select filter as one button and a menu of ticks (first used for
	 * the biographies toolbar's Tradition / Place / Era; shelf-agnostic). Twelve traditions and a dozen places used
	 * to sit above the list as two walls of chips (~400px before the first
	 * writer); here each facet is one control, and its menu says how many
	 * writers each tick leaves.
	 *
	 * Ticks apply as they are made — no Apply step, the list behind the menu is
	 * the feedback. `indent` nests a place under its region; `strong` marks the
	 * region itself.
	 */
	let {
		label,
		options,
		selected,
		ontoggle,
		onclear
	}: {
		label: string;
		options: FacetOption[];
		selected: string[];
		ontoggle: (v: string) => void;
		onclear: () => void;
	} = $props();

	const t = i18n.t;
	const menuId = $props.id();
	let open = $state(false);
	const on = $derived(new Set(selected));
</script>

<div class="relative" use:dismissable={{ open, onDismiss: () => (open = false) }}>
	<button
		type="button"
		class="filter-field facet-trigger"
		class:is-active={selected.length > 0}
		aria-expanded={open}
		aria-controls={open ? menuId : undefined}
		onclick={() => (open = !open)}
	>
		{label}{#if selected.length}<span class="rounded-full bg-accent-soft px-1.5 text-eyebrow font-semibold text-accent">{selected.length}</span>{/if}
		<svg class="facet-chev" class:open width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
	</button>
	{#if open}
		<!-- A labelled group of checkboxes, not role=menu: that promises arrow-key
		     menu navigation, and these are ordinary form controls (Tab moves
		     through them, Space ticks). -->
		<div id={menuId} class="account-menu facet-menu" role="group" aria-label={label}>
			<ul>
				{#each options as o (o.v)}
					<li>
						<label class="facet-option" class:indent={o.indent} class:strong={o.strong} class:empty={o.count === 0 && !on.has(o.v)}>
							<input type="checkbox" checked={on.has(o.v)} onchange={() => ontoggle(o.v)} />
							<span class="grow">{o.label}</span>
							<span class="facet-n">{o.count}</span>
						</label>
					</li>
				{/each}
			</ul>
			{#if selected.length}
				<div class="facet-foot">
					<button type="button" class="text-small font-semibold text-accent hover:underline" onclick={onclear}
						>{t('common.clearFilters')}</button
					>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.facet-trigger {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		cursor: pointer;
		white-space: nowrap;
	}
	.facet-chev {
		color: var(--muted);
		transition: transform var(--duration-base, 150ms);
	}
	.facet-chev.open {
		transform: rotate(180deg);
	}
	/* .account-menu is the shared popover chrome; this opens it start-side and
	   lets a long list scroll. */
	.facet-menu {
		inset-inline-start: 0;
		inset-inline-end: auto;
		width: 18rem;
		max-height: min(26rem, 70vh);
		overflow-y: auto;
	}
	.facet-option {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		min-height: 2.25rem;
		padding: 0.2rem 0.6rem;
		border-radius: var(--radius-sm);
		font-size: var(--fs-small);
		color: var(--text);
		cursor: pointer;
	}
	.facet-option:hover {
		background: var(--surface-2);
	}
	.facet-option:has(input:checked) {
		background: var(--accent-soft);
	}
	.facet-option.indent {
		padding-inline-start: 2rem;
	}
	.facet-option.strong {
		font-weight: 600;
	}
	.facet-option.empty {
		color: var(--muted);
	}
	.facet-option input {
		width: 1rem;
		height: 1rem;
		margin: 0;
		accent-color: var(--accent);
		flex-shrink: 0;
	}
	.facet-n {
		color: var(--muted);
		font-size: var(--fs-micro);
		font-variant-numeric: tabular-nums;
	}
	.facet-foot {
		display: flex;
		justify-content: flex-end;
		border-top: 1px solid var(--border);
		margin-top: 0.35rem;
		padding: 0.5rem 0.6rem 0.25rem;
	}
	@media (pointer: coarse) {
		.facet-option {
			min-height: 2.75rem;
		}
	}
</style>
