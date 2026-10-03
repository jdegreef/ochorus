<script lang="ts">
	import Icon from './Icon.svelte';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * Grid or list — the last control in a shelf's filter row (search · filters ·
	 * sort · group · view), always grid first, the same icons on every shelf.
	 * Each shelf keeps its own default view; only the control is shared.
	 * `cls`/`btnCls` let the phone sheet stretch it full width (`w-full`,
	 * `flex-1`), as the shelves' other segments do.
	 */
	export type ShelfView = 'grid' | 'list';
	let {
		view,
		onchange,
		cls = '',
		btnCls = ''
	}: {
		view: ShelfView;
		onchange: (v: ShelfView) => void;
		cls?: string;
		btnCls?: string;
	} = $props();
	const t = i18n.t;
</script>

<div class="seg {cls}" role="group" aria-label={t('bios.view')}>
	<button
		type="button"
		class={btnCls}
		class:active={view === 'grid'}
		onclick={() => onchange('grid')}
		aria-label={t('books.viewGrid')}
		aria-pressed={view === 'grid'}><Icon name="grid" /></button
	>
	<button
		type="button"
		class={btnCls}
		class:active={view === 'list'}
		onclick={() => onchange('list')}
		aria-label={t('books.viewList')}
		aria-pressed={view === 'list'}><Icon name="list" /></button
	>
</div>
