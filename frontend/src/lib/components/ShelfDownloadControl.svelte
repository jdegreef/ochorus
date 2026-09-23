<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { offlineBooks } from '$lib/offlineBooks.svelte';
	import { pwa } from '$lib/pwa.svelte';
	import { shelfDownload, type ShelfBookRef } from '$lib/shelfDownload.svelte';
	import Icon from './Icon.svelte';

	/**
	 * A Bookshelf shelf's "Download shelf" control, in the shelf's header. One
	 * control that changes with the state (see shelfDownload for the queue):
	 *
	 *   books still to save      → Download shelf (N)
	 *   this shelf downloading   → Downloading 3 of 8 · 40%   [Stop]
	 *   every book saved         → ✓ All saved offline   [Remove downloads]
	 *   last run had failures    → N couldn't be downloaded   [Try again]
	 *
	 * Offline, or while another shelf (or a single book) is downloading, the
	 * download button is disabled — `offlineBooks` runs one download at a time.
	 */
	let { shelf, books }: { shelf: string; books: ShelfBookRef[] } = $props();
	const t = i18n.t;

	// `offlineBooks.list()` reads its ticks, so a download or removal anywhere —
	// this shelf, the book page, Settings — re-derives these.
	const missing = $derived.by(() => {
		void offlineBooks.list();
		return shelfDownload.missing(books);
	});
	const mine = $derived(shelfDownload.job?.shelf === shelf ? shelfDownload.job : null);
	const busy = $derived(!!shelfDownload.job || !!offlineBooks.active);
	const result = $derived(shelfDownload.results[shelf]);
	// Overall progress: whole books done, plus the share of the one in hand.
	const percent = $derived.by(() => {
		if (!mine) return 0;
		const a = offlineBooks.active;
		const inBook = a && a.total ? a.done / a.total : 0;
		return Math.round(((mine.done + inBook) / mine.total) * 100);
	});
</script>

{#if books.length}
	<div class="ms-auto flex flex-wrap items-center justify-end gap-2 text-small">
		{#if mine}
			<span class="text-muted" aria-live="polite">
				{t('shelf.downloading')
					.replace('%n%', String(Math.min(mine.done + 1, mine.total)))
					.replace('%t%', String(mine.total))} · {percent}%
			</span>
			<button type="button" class="btn btn-sm" onclick={() => shelfDownload.stop()}
				>{t('shelf.stop')}</button
			>
		{:else if missing.length === 0}
			<span class="inline-flex items-center gap-1 text-muted">
				<Icon name="check" size={14} />
				{t('shelf.allSaved')}
			</span>
			<button
				type="button"
				class="btn btn-sm btn-ghost"
				disabled={busy}
				onclick={() => shelfDownload.removeAll(shelf, books)}>{t('shelf.removeDownloads')}</button
			>
		{:else}
			{#if result?.failed}
				<span class="text-muted"
					>{t('shelf.failed').replace('%n%', String(result.failed))}</span
				>
			{/if}
			<button
				type="button"
				class="btn btn-sm"
				disabled={busy || !pwa.online}
				title={pwa.online ? undefined : t('offline.needsConnection')}
				onclick={() => shelfDownload.start(shelf, books)}
			>
				<Icon name="download" size={15} />
				{result?.failed ? t('shelf.retry') : `${t('shelf.download')} (${missing.length})`}
			</button>
		{/if}
	</div>
{/if}
