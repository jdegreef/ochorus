<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { favorites } from '$lib/favorites.svelte';
	import { offlineBooks } from '$lib/offlineBooks.svelte';
	import { getBook } from '$lib/library-public';
	import {
		offerFinish,
		offerFinishUnopened,
		removeWork,
		restoreWork,
		unmarkFinished
	} from '$lib/progress';
	import { undo } from '$lib/undo.svelte';
	import { shelfHref, type ShelfBook } from '$lib/bookshelf';
	import Icon, { type IconName } from './Icon.svelte';

	/**
	 * What you can do with a book on the Bookshelf, as a list of `.account-item`
	 * rows — the same rows inside the covers view's "⋯" menu and the spines
	 * view's pulled-out book, so the two views can't offer different things.
	 *
	 *   Reading  → Resume · Mark as finished · Remove from shelf
	 *   To read  → Begin reading · I've already read this · Remove from shelf
	 *   Finished → Read again · Move back to reading · Remove from shelf
	 *   all      → Download for offline (or its progress / "Saved offline")
	 *
	 * "Remove from shelf" takes the book off whichever shelf it is on: it drops
	 * the reading position (progress.removeWork) and the heart, both of which
	 * the account tombstones so another device can't merge them back. One Undo
	 * puts back both. Highlights, notes and bookmarks in the book stay.
	 *
	 * Every state change goes through the progress/favorites stores, which bump
	 * their ticks or dispatch `ochorus:sync`, so the page re-shelves the book
	 * itself; `onDone` just lets the host close its menu or panel.
	 */
	let { item, onDone }: { item: ShelfBook; onDone: () => void } = $props();
	const t = i18n.t;

	const book = $derived(item.book);
	const primary = $derived.by(() => {
		if (item.status === 'reading')
			return { href: shelfHref(item), label: `${t('reader.resume')} · ${t('continue.chapter')} ${item.order}` };
		if (item.status === 'finished')
			return { href: `/books/${book.slug}/1`, label: t('fav.readAgain') };
		return { href: `/books/${book.slug}`, label: t('book.beginReading') };
	});

	const saved = $derived(offlineBooks.has(book.slug, book.language));
	const active = $derived(
		offlineBooks.active?.slug === book.slug && offlineBooks.active.language === book.language
			? offlineBooks.active
			: null
	);
	let failed = $state(false);

	function act(fn: () => void) {
		fn();
		onDone();
	}

	async function download() {
		failed = false;
		if (!navigator.onLine) {
			failed = true;
			return;
		}
		try {
			// The download needs the real chapter list (orders aren't always 1..n),
			// which only the book detail carries.
			const detail = await getBook(book.slug, book.language);
			failed = !(await offlineBooks.download(detail));
		} catch {
			failed = true;
		}
	}

	function removeFromShelf() {
		const slug = book.slug;
		const hearted = favorites.has('book', slug);
		const rec = removeWork(slug, 'book');
		if (hearted) favorites.toggle('book', slug);
		undo.offer({
			restore: () => {
				if (rec) restoreWork(slug, rec, 'book');
				if (hearted && !favorites.has('book', slug)) favorites.toggle('book', slug);
			}
		});
	}
</script>

{#snippet row(icon: IconName, label: string)}
	<span class="flex items-center gap-2.5">
		<span class="text-muted"><Icon name={icon} size={16} /></span>
		{label}
	</span>
{/snippet}

<a class="account-item font-semibold" href={localizeHref(primary.href)} onclick={onDone}>
	{@render row(item.status === 'finished' ? 'skip-back' : 'play', primary.label)}
</a>

{#if item.status === 'reading'}
	<button class="account-item" onclick={() => act(() => offerFinish(book.slug, 'book'))}>
		{@render row('check', t('continue.markFinished'))}
	</button>
{:else if item.status === 'toRead'}
	<button
		class="account-item"
		onclick={() =>
			act(() => offerFinishUnopened(book.slug, book.chapter_count, book.language, 'book'))}
	>
		{@render row('check', t('fav.alreadyRead'))}
	</button>
{:else}
	<button class="account-item" onclick={() => act(() => unmarkFinished(book.slug, 'book'))}>
		{@render row('bookmark', t('settings.unfinish'))}
	</button>
{/if}

{#if saved}
	<div class="account-item muted">
		{@render row('check', t('offline.saved'))}
	</div>
{:else if active}
	<div class="account-item muted" aria-live="polite">
		{@render row('download', `${t('offline.downloading')} ${active.done} / ${active.total}`)}
	</div>
{:else}
	<button class="account-item" onclick={download} disabled={!!offlineBooks.active}>
		{@render row('download', failed ? t('offline.needsConnection') : t('offline.download'))}
	</button>
{/if}

<div class="my-1 border-t border-border"></div>
<button class="account-item danger" onclick={() => act(removeFromShelf)}>
	{@render row('close', t('fav.removeFromShelf'))}
</button>

<style>
	/* Two classes, so these outrank .account-item's own colour. */
	.account-item.danger {
		color: var(--color-danger);
	}
	.account-item.muted {
		color: var(--color-muted);
		cursor: default;
	}
	.account-item.muted:hover {
		background: transparent;
	}
</style>
