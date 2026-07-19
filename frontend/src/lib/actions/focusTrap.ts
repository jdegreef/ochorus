/**
 * Focus-trap action for popovers and dialogs.
 *
 * Applied to an element that mounts when the overlay opens (typically inside an
 * `{#if open}` block), it:
 *  - moves focus into the overlay on open (first focusable, else the node),
 *  - keeps Tab / Shift+Tab cycling inside it,
 *  - calls `onEscape` when Escape is pressed,
 *  - returns focus to whatever was focused before it opened, on destroy.
 *
 * This is the pattern TocDrawer implemented inline; extracting it keeps every
 * overlay (CommandPalette, LanguagePicker, the reader note editor) consistent
 * instead of each re-solving keyboard access — or, as several did, not at all.
 */
const FOCUSABLE =
	'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export interface FocusTrapOptions {
	onEscape?: () => void;
	/** Skip the auto-focus-in (e.g. the overlay focuses a specific field itself). */
	autoFocus?: boolean;
}

export function focusTrap(node: HTMLElement, options: FocusTrapOptions = {}) {
	let opts = options;
	const opener = document.activeElement as HTMLElement | null;

	const focusables = () =>
		[...node.querySelectorAll<HTMLElement>(FOCUSABLE)].filter(
			(el) => el.offsetParent !== null || el === document.activeElement
		);

	if (opts.autoFocus !== false) {
		queueMicrotask(() => (focusables()[0] ?? node).focus());
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.stopPropagation();
			opts.onEscape?.();
			return;
		}
		if (e.key !== 'Tab') return;
		const f = focusables();
		if (!f.length) {
			e.preventDefault();
			return;
		}
		const first = f[0];
		const last = f[f.length - 1];
		if (e.shiftKey && document.activeElement === first) {
			e.preventDefault();
			last.focus();
		} else if (!e.shiftKey && document.activeElement === last) {
			e.preventDefault();
			first.focus();
		}
	}

	node.addEventListener('keydown', onKeydown);

	return {
		update(next: FocusTrapOptions = {}) {
			opts = next;
		},
		destroy() {
			node.removeEventListener('keydown', onKeydown);
			// Return focus to whatever opened the overlay. (By destroy time the
			// overlay's focused child is already being removed, so activeElement
			// has fallen to <body> — an "is focus still inside?" guard would wrongly
			// skip the restore. Focusing a since-detached opener is a harmless
			// no-op, e.g. when the overlay closed by navigating away.)
			opener?.focus?.();
		}
	};
}
