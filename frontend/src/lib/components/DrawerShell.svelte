<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import type { Snippet } from 'svelte';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * The shared shell for the reader's slide-over drawers (contents, search,
	 * notes). It owns the scrim, the panel chrome, the dialog semantics, the
	 * focus trap + Escape-to-close, the standard header (title + close button),
	 * and the slide-in animation. Each drawer supplies only its own header extras
	 * and body.
	 *
	 * The drawer belongs at the END of the reading direction, which under
	 * dir="rtl" (Arabic) is the LEFT edge — so it is anchored (inset-inline-end),
	 * bordered (border-inline-start) and slid logically, and everything follows
	 * the inline axis on its own. Box-shadow offsets and translateX have no
	 * logical form, so those two alone are flipped explicitly under RTL below.
	 */
	let {
		open = $bindable(false),
		title = '',
		ariaLabel = title,
		width,
		autoFocus = true,
		placement = 'end',
		titleArea,
		headerExtra,
		children
	}: {
		open?: boolean;
		/** Visible header title; ignored when a `titleArea` snippet is given. */
		title?: string;
		/**
		 * Accessible name for the dialog. Defaults to `title`; set it only when the
		 * accessible name must differ from (or stand in for) the visible title —
		 * e.g. TocDrawer, whose visible heading is the book title but whose dialog
		 * is named "Contents".
		 */
		ariaLabel?: string;
		/** Panel width; defaults to min(24rem, 92vw). */
		width?: string;
		/** Skip auto-focus-in when the drawer focuses a field of its own. */
		autoFocus?: boolean;
		/**
		 * `end` slides in from the reading-direction end (the default);
		 * `bottom` is a phone bottom sheet — full width, rounded top, a grab
		 * handle, capped at 85vh with its body scrolling.
		 */
		placement?: 'end' | 'bottom';
		/** Custom title block (e.g. title + subtitle), replacing `title`. */
		titleArea?: Snippet;
		/** Extra header content below the title row (e.g. a search field). */
		headerExtra?: Snippet;
		children: Snippet;
	} = $props();

	const t = i18n.t;

	function close() {
		open = false;
	}

	// focusTrap catches Escape while focus is inside the panel (and stops it
	// there); this window fallback still closes the drawer if focus has fallen
	// elsewhere — e.g. onto <body>. (`<svelte:window>` can't live inside the
	// {#if open} block, so it stays mounted and guards on `open` itself.)
	function onKeydown(e: KeyboardEvent) {
		if (open && e.key === 'Escape') {
			e.stopPropagation();
			close();
		}
	}
</script>

<svelte:window onkeydown={onKeydown} />

{#if open}
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="drawer-scrim" onclick={close}></div>
	<!-- focusTrap keeps Tab inside the panel, moves focus in on open (unless the
	     drawer focuses its own field, autoFocus=false), returns it to the opener
	     on close, and handles Escape while focus is inside. -->
	<div
		class="drawer-panel"
		class:bottom={placement === 'bottom'}
		role="dialog"
		aria-modal="true"
		aria-label={ariaLabel}
		style={width ? `--drawer-width: ${width}` : undefined}
		use:focusTrap={{ onEscape: close, autoFocus }}
	>
		{#if placement === 'bottom'}
			<div class="drawer-handle" aria-hidden="true"></div>
		{/if}
		<header class="border-b border-border px-5 py-4">
			<div class="flex items-center justify-between gap-3">
				{#if titleArea}
					{@render titleArea()}
				{:else}
					<h2 class="text-h3 text-text">{title}</h2>
				{/if}
				<button class="btn btn-icon btn-ghost" onclick={close} aria-label={t('a11y.close')}
					><Icon name="close" /></button
				>
			</div>
			{#if headerExtra}
				{@render headerExtra()}
			{/if}
		</header>
		{@render children()}
	</div>
{/if}

<style>
	.drawer-scrim {
		position: fixed;
		inset: 0;
		z-index: 48;
		background: rgb(0 0 0 / 0.35);
	}
	.drawer-panel {
		position: fixed;
		top: 0;
		bottom: 0;
		inset-inline-end: 0;
		z-index: 49;
		width: var(--drawer-width, min(24rem, 92vw));
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-inline-start: 1px solid var(--border);
		box-shadow: var(--shadow-drawer);
		--drawer-slide-from: 1.5rem;
		animation: drawer-in var(--duration-fast) ease-out;
	}
	:global([dir='rtl']) .drawer-panel {
		box-shadow: 12px 0 40px rgb(0 0 0 / 0.25);
		--drawer-slide-from: -1.5rem;
	}
	.drawer-panel.bottom {
		top: auto;
		inset-inline: 0;
		width: auto;
		max-height: 85vh;
		border-inline-start: 0;
		border-top: 1px solid var(--border);
		border-radius: 1.25rem 1.25rem 0 0;
		box-shadow: 0 -12px 40px rgb(0 0 0 / 0.25);
		animation-name: sheet-in;
	}
	.drawer-handle {
		width: 2.4rem;
		height: 0.25rem;
		margin: 0.5rem auto 0;
		border-radius: 999px;
		background: var(--border-strong);
	}
	@keyframes sheet-in {
		from {
			transform: translateY(2rem);
			opacity: 0;
		}
	}
	@keyframes drawer-in {
		from {
			transform: translateX(var(--drawer-slide-from, 1.5rem));
			opacity: 0;
		}
	}
</style>
