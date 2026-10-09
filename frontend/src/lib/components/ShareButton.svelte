<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { dismissable } from '$lib/actions/dismissable';
	import { menuShift } from '$lib/menuShift';
	import { nativeShare, shareLinks } from '$lib/share';

	/**
	 * The one share control for a leaf page (book / sermon / article / author /
	 * plan / topic), so "share" reads and behaves the same everywhere — the
	 * front door to the per-edition share card the build already generates
	 * (`shareCard`/og-manifest), which is what a forwarded link previews.
	 *
	 * Client-only by design (static SPA): on click it uses the OS share sheet
	 * on a touch device whose browser has one (`navigator.share` — most
	 * phones), and otherwise opens a small menu — Copy link, WhatsApp,
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
		/** The button's words, where a page asks for something warmer than
		 *  "Share" ("Share with a family"). */
		label?: string;
		/** `md`: the full-size labelled button, beside a full-size primary in a
		 *  banner's call-to-action row (the young-reader hubs). */
		size?: 'sm' | 'md';
		/** Called when the page is passed on: the OS sheet completes, the link
		 *  is copied, or a share target is chosen — not on a dismissed sheet. */
		onshare?: () => void;
	}
	let { url, title, showLabel = false, label, size = 'sm', onshare }: Props = $props();
	const t = i18n.t;
	const name = $derived(label ?? t('reader.share'));
	const menuId = $props.id();

	let open = $state(false);
	let root = $state<HTMLDivElement>();
	// Placed by `menuShift` from the button's start edge, so a button near the
	// screen's end edge on a phone can't hang the menu off it.
	let width = $state(192);
	let shift = $state(0);
	function toggle() {
		if (!open && root) ({ width, shift } = menuShift(root, 192));
		open = !open;
	}
	let copied = $state(false);
	let copyTimer: ReturnType<typeof setTimeout> | undefined;
	$effect(() => () => clearTimeout(copyTimer));

	const links = $derived(shareLinks(title, url, t('login.email')));

	async function onClick() {
		// Any failure other than a dismissed sheet falls through to the menu.
		const result = await nativeShare(title, url);
		if (result === 'shared') onshare?.();
		else if (result === 'unavailable') toggle();
	}

	async function copyLink() {
		try {
			await navigator.clipboard.writeText(url);
			onshare?.();
			copied = true;
			clearTimeout(copyTimer);
			copyTimer = setTimeout(() => (copied = false), 1500);
		} catch {
			// Clipboard blocked (older desktop app views): leave the menu open so
			// the reader can copy the address from the location bar instead.
		}
	}
</script>

<div class="share-wrap" bind:this={root} use:dismissable={{ open, onDismiss: () => (open = false) }}>
	<button
		type="button"
		class="btn btn-ghost {!showLabel ? 'btn-icon' : size === 'sm' ? 'btn-sm' : ''}"
		onclick={onClick}
		aria-controls={open ? menuId : undefined}
		aria-expanded={open}
		aria-label={name}
		title={name}
	>
		<Icon name="share" size={18} strokeWidth={1.7} />
		{#if showLabel}<span class="btn-label">{name}</span>{/if}
	</button>

	{#if open}
		<!-- A labelled group, not a menu role: that promises arrow-key
		     navigation between menu items, and these are plain links and buttons
		     reached with Tab — the same treatment as AccountMenu/QuickSettings. -->
		<div
			id={menuId}
			class="share-menu"
			style:width="{width}px"
			style:left="{shift}px"
			role="group"
			aria-label={name}
		>
			<button type="button" class="share-opt text-small" onclick={copyLink}>
				{copied ? t('share.linkCopied') : t('share.copyLink')}
			</button>
			{#each links as l (l.name)}
				<a
					class="share-opt text-small"
					href={l.href}
					target={l.newTab ? '_blank' : undefined}
					rel={l.newTab ? 'noopener' : undefined}
					onclick={() => {
						onshare?.();
						open = false;
					}}>{l.name}</a
				>
			{/each}
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
		/* Physical `left`/`width` from the script (see `toggle`). */
		left: 0; /* rtl-ok: physical offset set from script, already direction-aware (menuShift) */
		z-index: var(--z-popover);
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
