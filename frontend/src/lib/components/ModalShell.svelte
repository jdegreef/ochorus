<script lang="ts">
	import type { Snippet } from 'svelte';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { portal } from '$lib/actions/portal';

	/**
	 * The shared shell for a centred modal dialog — DrawerShell's sibling for
	 * the note editor, the Notebook's journal and testimony dialogs, feedback
	 * and the unsynced sign-out prompt. It owns the scrim, the card chrome, the
	 * dialog semantics and the focus trap + Escape-to-close; each dialog
	 * supplies only its content.
	 *
	 * It is portalled to <body>, so a caller may render it anywhere — inside a
	 * transformed `.page-col`, the page-turn pager or a backdrop-filtered bar —
	 * and it still covers the viewport. The overlay is this component's ONLY
	 * root element, which is what makes moving it safe: see
	 * `$lib/actions/portal`.
	 *
	 * Mount it while the dialog is open (`{#if open}<ModalShell …>`); it has no
	 * `open` prop of its own. The card scrolls within the viewport when its
	 * content is taller than the screen.
	 *
	 * Unlike a drawer, a click on the scrim does NOT close it: these dialogs
	 * hold a draft (a note, a prayer, feedback) or ask a question that needs an
	 * answer, and a stray tap outside the card must not throw either away.
	 * Escape and each dialog's own Cancel close it.
	 */
	let {
		onClose,
		role = 'dialog',
		ariaLabel,
		ariaLabelledby,
		ariaDescribedby,
		width = '32rem',
		initialFocus,
		children
	}: {
		/** Escape, from anywhere inside the dialog. */
		onClose: () => void;
		/** `alertdialog` for a prompt that interrupts to ask something. */
		role?: 'dialog' | 'alertdialog';
		/** The accessible name — or name it by a heading with `ariaLabelledby`. */
		ariaLabel?: string;
		ariaLabelledby?: string;
		ariaDescribedby?: string;
		/** The card's max width. */
		width?: string;
		/** Selector for what takes focus on open (default: the first focusable). */
		initialFocus?: string;
		children: Snippet;
	} = $props();
</script>

<div
	class="modal-overlay"
	use:portal
	{role}
	aria-modal="true"
	aria-label={ariaLabel}
	aria-labelledby={ariaLabelledby}
	aria-describedby={ariaDescribedby}
	use:focusTrap={{ onEscape: onClose, initialFocus }}
>
	<div class="modal-card" style:max-width={width}>
		{@render children()}
	</div>
</div>

<style>
	.modal-overlay {
		position: fixed;
		inset: 0;
		z-index: var(--z-modal);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		background: rgb(0 0 0 / 0.4);
	}
	.modal-card {
		width: 100%;
		max-height: calc(100dvh - 2rem);
		overflow-y: auto;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		padding: 1.25rem;
		box-shadow: var(--shadow-popover);
	}
</style>
