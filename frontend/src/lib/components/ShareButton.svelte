<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { dismissable } from '$lib/actions/dismissable';

	/**
	 * The one share control for a leaf page (book / sermon / article / author /
	 * plan / topic), so "share" reads and behaves the same everywhere — the
	 * front door to the per-edition share card the build already generates
	 * (`shareCard`/og-manifest), which is what a forwarded link previews.
	 *
	 * Client-only by design (static SPA): on click it uses the OS share sheet
	 * where the browser has one (`navigator.share` — most phones and some
	 * desktops), and otherwise opens a small menu — Copy link, WhatsApp,
	 * Facebook, Email. WhatsApp leads because that is how this content travels.
	 * The button always renders (no prerender branch); the capability check and
	 * the menu are decided at click time.
	 *
	 * `showLabel` picks the shape like FavoriteButton: a labelled `.btn-sm` for a
	 * leaf-page action row, else an icon-only `.btn-icon`.
	 */
	interface Props {
		/** Absolute, per-locale URL to share (the page's canonical). */
		url: string;
		/** Human title for the share ("Title — Author"). */
		title: string;
		showLabel?: boolean;
	}
	let { url, title, showLabel = false }: Props = $props();
	const t = i18n.t;
	const menuId = $props.id();

	let open = $state(false);
	let copied = $state(false);

	const enc = encodeURIComponent;
	// Service names (WhatsApp, Facebook) are proper nouns — not localized, like
	// the artwork credit. "Share"/"Email" reuse existing catalogue strings.
	const waHref = $derived(`https://wa.me/?text=${enc(`${title} ${url}`)}`);
	const fbHref = $derived(`https://www.facebook.com/sharer/sharer.php?u=${enc(url)}`);
	const mailHref = $derived(`mailto:?subject=${enc(title)}&body=${enc(`${title}\n\n${url}`)}`);

	async function onClick() {
		if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
			try {
				await navigator.share({ title, url });
				return;
			} catch (err) {
				// The reader dismissed the sheet — do nothing. Any other failure
				// (unsupported payload, etc.) falls through to the menu.
				if ((err as Error)?.name === 'AbortError') return;
			}
		}
		open = !open;
	}

	async function copyLink() {
		try {
			await navigator.clipboard.writeText(url);
			copied = true;
			setTimeout(() => (copied = false), 1500);
		} catch {
			// Clipboard blocked (older desktop app views): leave the menu open so
			// the reader can copy the address from the location bar instead.
		}
	}
</script>

<div class="share-wrap" use:dismissable={{ open, onDismiss: () => (open = false) }}>
	<button
		type="button"
		class="btn btn-ghost {showLabel ? 'btn-sm' : 'btn-icon'}"
		onclick={onClick}
		aria-controls={open ? menuId : undefined}
		aria-expanded={open}
		aria-label={t('reader.share')}
		title={t('reader.share')}
	>
		<svg
			width="18"
			height="18"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="1.7"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<circle cx="6" cy="12" r="2.6" />
			<circle cx="17" cy="6" r="2.6" />
			<circle cx="17" cy="18" r="2.6" />
			<path d="M8.3 10.9 14.7 7.2M8.3 13.1l6.4 3.7" />
		</svg>
		{#if showLabel}<span class="btn-label">{t('reader.share')}</span>{/if}
	</button>

	{#if open}
		<!-- A labelled group, not a menu role: that promises arrow-key
		     navigation between menu items, and these are plain links and buttons
		     reached with Tab — the same treatment as AccountMenu/QuickSettings. -->
		<div id={menuId} class="share-menu" role="group" aria-label={t('reader.share')}>
			<button type="button" class="share-opt text-small" onclick={copyLink}>
				{copied ? t('share.linkCopied') : t('share.copyLink')}
			</button>
			<a
				class="share-opt text-small"
				href={waHref}
				target="_blank"
				rel="noopener"
				onclick={() => (open = false)}>WhatsApp</a
			>
			<a
				class="share-opt text-small"
				href={fbHref}
				target="_blank"
				rel="noopener"
				onclick={() => (open = false)}>Facebook</a
			>
			<a class="share-opt text-small" href={mailHref} onclick={() => (open = false)}
				>{t('login.email')}</a
			>
		</div>
	{/if}
</div>

<style>
	.share-wrap {
		position: relative;
		display: inline-flex;
	}
	.share-menu {
		position: absolute;
		top: calc(100% + 0.4rem);
		inset-inline-start: 0;
		z-index: 30;
		min-width: 12rem;
		padding: 0.35rem;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		box-shadow: 0 12px 28px rgb(0 0 0 / 0.22);
	}
	.share-opt {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		width: 100%;
		padding: 0.5rem 0.6rem;
		border: 0;
		border-radius: 8px;
		background: transparent;
		color: var(--text);
		font: inherit;
		text-align: start;
		text-decoration: none;
		cursor: pointer;
	}
	.share-opt:hover {
		background: var(--surface-2);
	}
	.share-opt:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: -2px;
	}
</style>
