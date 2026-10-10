<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { API_BASE_URL } from '$lib/config';
	import type { BookDetail } from '$lib/library-public';
	import { offlineBooks } from '$lib/offlineBooks.svelte';
	import { IS_APP } from '$lib/platform';
	import { pwa } from '$lib/pwa.svelte';
	import { dismissable } from '$lib/actions/dismissable';
	import { menuShift } from '$lib/menuShift';
	import { mediaFlag } from '$lib/mediaFlag.svelte';
	import { PHONE } from '$lib/breakpoints';
	import DrawerShell from './DrawerShell.svelte';
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
	// `!IS_APP`, not `offlineBooks.supported`: that is false while prerendering
	// (no browser), and the button must be in the website's HTML, not pop in at
	// hydration. The app is the one place offline saving is off for everyone.
	const hasOptions = $derived(!IS_APP || savedOffline || !!book.epub_url || !!book.pdf_url);
	const pct = $derived(downloading?.total ? Math.round((downloading.done / downloading.total) * 100) : 0);

	// Phones (<640px) get a bottom sheet; wider screens the dropdown. mediaFlag
	// is false until hydrated, so the prerendered markup is the dropdown's.
	const phone = mediaFlag(PHONE);
	const isPhone = $derived(phone.matches);

	let open = $state(false);
	const dropdownOpen = $derived(open && !isPhone);
	// Crossing 640px while open (a phone rotated mid-choice) would show the
	// dropdown unmeasured — hung from the button's edge, possibly off-screen.
	// Close instead; the next tap opens the right shape, measured. (Runs on
	// every change of isPhone only; the first run, at hydration, finds the
	// menu closed already.)
	$effect(() => {
		void isPhone;
		open = false;
	});
	let root = $state<HTMLDivElement>();
	// Hung from the button's end edge like .account-menu, but placed by
	// `menuShift` so a mid-row button on a phone (and a long translated label)
	// can't push the menu off the screen's start edge.
	let width = $state(288);
	let shift = $state(0);
	function toggle() {
		if (!open && !isPhone && root) ({ width, shift } = menuShift(root, 288, 'end'));
		open = !open;
	}
</script>

<!-- The options, written once and shown either way: a dropdown hung from the
     button (640px up) or a bottom sheet (phones), so each presentation runs
     the same handlers. -->
{#snippet options()}
	{#if downloading}
		<span class="account-item dl-item text-muted">
			<Icon name="download" size={15} />
			<span class="dl-text"><span class="dl-label">{t('offline.downloading')} {pct}%</span></span>
		</span>
	{:else if savedOffline}
		<button
			type="button"
			class="account-item dl-item"
			title={t('offline.remove')}
			onclick={() => offlineBooks.remove(book.slug, book.language)}
		>
			<Icon name="check" size={15} />
			<span class="dl-text">
				<span class="dl-label">{t('offline.saved')}</span>
				<span class="hint">{t('offline.remove')}</span>
			</span>
		</button>
	{:else if offlineBooks.supported}
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
			<span class="dl-text"><span class="dl-label">{t('offline.download')}</span></span>
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
			<span class="dl-text">
				<span class="dl-label">EPUB</span>
				<span class="hint">{t('book.epubHint')}</span>
			</span>
		</a>
	{/if}
	{#if book.pdf_url}
		<a href={book.pdf_url} class="account-item dl-item" download onclick={() => (open = false)}>
			<Icon name="list" size={15} />
			<span class="dl-text">
				<span class="dl-label">PDF</span>
				<span class="hint">{t('book.pdfHint')}</span>
			</span>
		</a>
	{/if}
{/snippet}

<!-- Nothing to offer (no offline save on this device, and no EPUB or PDF for
     this edition): no button, rather than one that opens an empty menu. -->
{#if hasOptions}
	<!-- dismissable only for the dropdown: the sheet is portalled to <body>, so a
	     tap inside it would read as a click away; DrawerShell owns its own scrim,
	     Escape and focus return. -->
	<div
		class="relative"
		bind:this={root}
		use:dismissable={{ open: dropdownOpen, onDismiss: () => (open = false) }}
	>
		<button
			type="button"
			class="btn btn-sm btn-ghost"
			aria-controls={dropdownOpen ? menuId : undefined}
			aria-haspopup={isPhone ? 'dialog' : undefined}
			aria-expanded={open}
			onclick={toggle}
		>
			<Icon name={savedOffline ? 'check' : 'download'} size={15} />
			<span>{downloading ? `${pct}%` : t('book.download')}</span>
		</button>
		{#if dropdownOpen}
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
				{@render options()}
			</div>
		{/if}
	</div>

	{#if isPhone}
		<DrawerShell bind:open title={t('book.download')} placement="bottom">
			<div class="dl-sheet">{@render options()}</div>
		</DrawerShell>
	{/if}
{/if}

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
	/* Dropdown: label and hint share one line, the hint trailing. */
	.dl-text {
		flex: 1;
		min-width: 0;
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
	}
	.dl-label {
		flex: 1;
	}
	.hint {
		font-size: var(--fs-eyebrow);
		color: var(--muted);
	}

	/* Sheet: full-width rows, the format's name over what it is for. */
	.dl-sheet {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}
	.dl-sheet .dl-item {
		max-width: none;
		min-height: 3.5rem;
		padding: 0.6rem 0.75rem;
		gap: 0.85rem;
		font-size: var(--fs-body);
		white-space: normal;
		overflow-wrap: anywhere;
	}
	.dl-sheet .dl-text {
		flex-direction: column;
		align-items: stretch;
		gap: 0.15rem;
	}
	.dl-sheet .dl-label {
		font-weight: 600;
	}
	.dl-sheet .hint {
		font-size: var(--fs-small);
	}
</style>
