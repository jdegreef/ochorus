<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { customShelves } from '$lib/customShelves.svelte';
	import { dismissable } from '$lib/actions/dismissable';
	import Icon from './Icon.svelte';
	import ShelfPicker from './ShelfPicker.svelte';

	/**
	 * The book page's "Add to a shelf": puts the book on the reader's own
	 * Bookshelf shelves without going to the Bookshelf first — the only way to
	 * shelve a book that isn't already there. A `.btn-sm` like its Share and
	 * Download neighbours, opening a small menu with the ShelfPicker.
	 *
	 * Labelled with how many of the reader's shelves already hold the book, so
	 * the page shows at a glance that it's shelved. Client state only
	 * (localStorage), so on the prerendered page it starts as a plain button
	 * and fills in on hydration.
	 */
	// `shortLabel` renders both labels: the `.action-strip` shows "Shelf" when it
	// is an icon strip (no room for "Add to a shelf" in a fifth of it) and the
	// long label when it is a row. Without an .action-strip, CSS shows both, so
	// only pass it inside one.
	let { slug, shortLabel = false }: { slug: string; shortLabel?: boolean } = $props();
	const t = i18n.t;

	let open = $state(false);
	let root = $state<HTMLDivElement>();
	// Placed from the BUTTON, not by measuring the menu: on a phone the button
	// can wrap to mid-row, where a menu hung from it runs off the screen (and
	// scrolls the page sideways), and a menu measured as it opens is measured
	// before its contents have laid out. So the menu gets a known width —
	// at most 18rem, never wider than the screen less 8px a side — and is
	// slid from the button's start edge just enough to stay inside the screen.
	let width = $state(288);
	let shift = $state(0);
	function toggle() {
		if (!open && root) {
			const vw = document.documentElement.clientWidth;
			const btn = root.getBoundingClientRect();
			width = Math.min(288, vw - 16);
			const left = Math.min(Math.max(btn.left, 8), vw - 8 - width);
			shift = left - btn.left;
		}
		open = !open;
	}
	const onCount = $derived(customShelves.list().filter((s) => customShelves.has(s.id, slug)).length);
</script>

<div
	class="relative"
	bind:this={root}
	use:dismissable={{ open, onDismiss: () => (open = false) }}
>
	<button
		type="button"
		class="btn btn-sm btn-ghost"
		aria-expanded={open}
		onclick={toggle}
	>
		<Icon name="layers" size={15} />
		{#if shortLabel}
			<span class="label-long">{t('shelves.addTo')}</span><span class="label-short"
				>{t('shelves.short')}</span
			>
		{:else}
			{t('shelves.addTo')}
		{/if}
		{#if onCount}
			<span class="shelf-count" aria-hidden="true">✓ {onCount}</span>
		{/if}
	</button>
	{#if open}
		<div
			class="account-menu picker"
			style:width="{width}px"
			style:left="{shift}px"
			role="group"
			aria-label={t('shelves.addTo')}
		>
			<ShelfPicker {slug} />
		</div>
	{/if}
</div>

<style>
	.shelf-count {
		margin-inline-start: 0.15rem;
		font-size: var(--fs-eyebrow);
		font-weight: 700;
		color: var(--color-accent);
	}
	/* Physical `left` from the script (see `toggle`) — the placement is in
	   screen pixels, so it's the same in RTL. Two classes, to outrank the
	   unlayered .account-menu. */
	.account-menu.picker {
		inset-inline: auto;
		min-width: 0;
	}
</style>
