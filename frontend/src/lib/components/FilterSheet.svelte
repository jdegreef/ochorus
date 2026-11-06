<script lang="ts">
	import type { Snippet } from 'svelte';
	import { mediaFlag } from '$lib/mediaFlag.svelte';
	import DrawerShell from '$lib/components/DrawerShell.svelte';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * A shelf's phone filters: the "Filters" button that sits beside the search
	 * field, and the bottom sheet it opens. Below sm a shelf's filter row is just
	 * search + this button — four stacked controls were ~300px before the first
	 * result — and the sheet holds the same controls as one-tap choices. From sm
	 * the button hides and the page's inline controls take over.
	 *
	 * `everywhere` keeps the button at every width, for a shelf whose bar is
	 * search · sort · ONE Filters button · view (Books, design review #15): its
	 * facets live only here. From sm the same panel opens as a side sheet at
	 * the reading-direction end instead of a bottom sheet, and widening the
	 * window leaves it open.
	 *
	 * The page owns the controls (its `children`, usually snippets it also
	 * renders inline) and what they narrow; this owns the button, the count on
	 * it, the sheet, and its footer. A labelled chip group inside is a
	 * <SheetChoices>. The sheet portals to <body>
	 * (DrawerShell), so it can sit anywhere in the page's markup.
	 */
	let {
		open = $bindable(false),
		count,
		shown,
		showLabel,
		filtered,
		onClear,
		everywhere = false,
		children
	}: {
		open?: boolean;
		/** How many sheet controls are narrowing the list — on the button, so a
		 *  closed sheet can't hide that the list is filtered. Sort and grouping
		 *  arrange rather than narrow, so they don't count. */
		count: number;
		/** Results after every filter, for the "Show … (N)" button. */
		shown: number;
		/** That button's label, with `%n%` for the count. */
		showLabel: string;
		/** Whether anything narrows the list (search and topic included) — the
		 *  sheet offers `onClear` while it does. */
		filtered: boolean;
		onClear?: () => void;
		/** Offer the button at every width, not just below sm (see above). */
		everywhere?: boolean;
		children: Snippet;
	} = $props();

	const t = i18n.t;

	// The sheet is a phone control: widen past sm (a tablet rotating) and the
	// inline row takes over, so close it rather than leave it over the page —
	// unless there is no inline row (`everywhere`): then it opens as a side
	// sheet from sm. Its form is fixed when it opens — switching it under an
	// open panel would remount the controls and drop the focus inside it.
	const wide = mediaFlag('(min-width: 640px)');
	$effect(() => {
		if (open && wide.matches && !everywhere) open = false;
	});
	let side = $state(false);
	function show() {
		side = everywhere && wide.matches;
		open = true;
	}
</script>

<button
	class="chip flex shrink-0 items-center gap-1.5 {everywhere ? '' : 'sm:hidden'}"
	onclick={show}
	aria-haspopup="dialog"
	aria-expanded={open}
>
	{t('common.filters')}
	{#if count}
		<span class="rounded-full bg-accent-soft px-1.5 text-eyebrow font-semibold text-accent">{count}</span>
	{/if}
</button>

<DrawerShell bind:open title={t('common.filters')} placement={side ? 'end' : 'bottom'}>
	<!-- A side drawer leaves its body to the caller (DrawerShell): here it
	     scrolls under the header and the footer stays in reach below it. -->
	<div class="filter-sheet" class:side-scroll={side}>
		{@render children()}
	</div>
	<!-- The list updates behind the sheet as the choices change; this closes it. -->
	<div class="flex items-center gap-2" class:mt-6={!side} class:side-foot={side}>
		{#if filtered && onClear}
			<button class="btn btn-ghost" onclick={onClear}>{t('common.clearFilters')}</button>
		{/if}
		<button class="btn btn-primary flex-1" onclick={() => (open = false)}
			>{showLabel.replace('%n%', String(shown))}</button
		>
	</div>
</DrawerShell>

<style>
	.side-scroll {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overscroll-behavior: contain;
		padding: 1rem 1.25rem 1.5rem;
	}
	.side-foot {
		border-top: 1px solid var(--border);
		padding: 0.875rem 1.25rem;
	}
	/* The page's controls stack at one rhythm; SheetChoices groups, a select, a
	   segmented control all sit on it without margins of their own. */
	.filter-sheet {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}
</style>
