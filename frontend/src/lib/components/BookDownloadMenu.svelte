<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { API_BASE_URL } from '$lib/config';
	import type { BookDetail } from '$lib/library-public';
	import { offlineBooks } from '$lib/offlineBooks.svelte';
	import { pwa } from '$lib/pwa.svelte';
	import { dismissable } from '$lib/actions/dismissable';
	import { menuShift } from '$lib/menuShift';
	import Icon from './Icon.svelte';

	/**
	 * The book page's one "Download" control: offline reading in the app, an
	 * EPUB for an e-reader, a PDF to print. One verb, so one button with a menu,
	 * each option saying what it is FOR (most readers don't know what an EPUB
	 * is).
	 *
	 * Offline state is per EDITION: `book.language` is the language the API
	 * served, so it is what was cached and what must be asked for. EPUB is built
	 * per request by the API (`epub_url` is "" for an edition export_policy does not list); the PDF is either a
	 * static file under /pdfs/ — no rel="external", so a pdf_url whose file is
	 * missing fails the prerender crawl instead of shipping a dead link — or a
	 * Supabase Storage URL (export_policy.STORED_PDF_EDITIONS), whose
	 * `?download=` makes it an attachment where a cross-origin `download` can't.
	 */
	let { book }: { book: BookDetail } = $props();
	const t = i18n.t;
	const menuId = $props.id();

	const savedOffline = $derived(offlineBooks.has(book.slug, book.language));
	const downloading = $derived(
		offlineBooks.active?.slug === book.slug && offlineBooks.active?.language === book.language
			? offlineBooks.active
			: null
	);
	const pct = $derived(downloading?.total ? Math.round((downloading.done / downloading.total) * 100) : 0);

	let open = $state(false);
	let root = $state<HTMLDivElement>();
	// Hung from the button's end edge like .account-menu, but placed by
	// `menuShift` so a mid-row button on a phone (and a long translated label)
	// can't push the menu off the screen's start edge.
	let width = $state(288);
	let shift = $state(0);
	function toggle() {
		if (!open && root) ({ width, shift } = menuShift(root, 288, 'end'));
		open = !open;
	}
</script>

<div class="relative" bind:this={root} use:dismissable={{ open, onDismiss: () => (open = false) }}>
	<button
		type="button"
		class="btn btn-sm btn-ghost"
		aria-controls={open ? menuId : undefined}
		aria-expanded={open}
		onclick={toggle}
	>
		<Icon name={savedOffline ? 'check' : 'download'} size={15} />
		<span>{downloading ? `${pct}%` : t('book.download')}</span>
	</button>
	{#if open}
		<!-- A labelled group, not a menu role: that promises arrow-key
		     navigation between menu items, and these are plain links and buttons
		     reached with Tab — the same treatment as AccountMenu/QuickSettings. -->
		<div
			id={menuId}
			class="account-menu dl-menu"
			style:width="{width}px"
			style:left="{shift}px"
			role="group"
			aria-label={t('book.download')}
		>
			{#if downloading}
				<span class="account-item dl-item text-muted">
					<Icon name="download" size={15} />
					{t('offline.downloading')} {pct}%
				</span>
			{:else if savedOffline}
				<button
					type="button"
					class="account-item dl-item"
					title={t('offline.remove')}
					onclick={() => offlineBooks.remove(book.slug, book.language)}
				>
					<Icon name="check" size={15} />
					<span class="flex-1">{t('offline.saved')}</span>
					<span class="hint">{t('offline.remove')}</span>
				</button>
			{:else}
				<button
					type="button"
					class="account-item dl-item"
					disabled={!pwa.online}
					title={pwa.online ? undefined : t('offline.needsConnection')}
					onclick={() => {
						offlineBooks.download(book);
						open = false;
					}}
				>
					<Icon name="download" size={15} />
					<span class="flex-1">{t('offline.download')}</span>
				</button>
			{/if}
			{#if book.epub_url}
				<a
					href={`${API_BASE_URL}${book.epub_url}`}
					class="account-item dl-item"
					download
					rel="nofollow"
					onclick={() => (open = false)}
				>
					<Icon name="book" size={15} />
					<span class="flex-1">EPUB</span>
					<span class="hint">{t('book.epubHint')}</span>
				</a>
			{/if}
			{#if book.pdf_url}
				<a
					href={book.pdf_url}
					class="account-item dl-item"
					download
					onclick={() => (open = false)}
				>
					<Icon name="list" size={15} />
					<span class="flex-1">PDF</span>
					<span class="hint">{t('book.pdfHint')}</span>
				</a>
			{/if}
		</div>
	{/if}
</div>

<style>
	/* Physical `left` from the script (see `toggle`). Two classes, to outrank
	   the unlayered .account-menu. */
	.account-menu.dl-menu {
		inset-inline: auto;
		min-width: 0;
	}
	.dl-item {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		max-width: calc(100vw - 2rem);
	}
	.dl-item:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.hint {
		font-size: var(--fs-eyebrow);
		color: var(--muted);
	}
</style>
