/**
 * Close-on-click-away / close-on-Escape for a dropdown menu.
 *
 * Apply to the element that wraps BOTH the trigger and its menu:
 *
 *   <div use:dismissable={{ open, onDismiss: () => (open = false) }}>
 *
 * While `open`, a click outside that element or an Escape press calls
 * `onDismiss`. When Escape closes a menu that had focus inside it, focus goes
 * back to the trigger (the wrapper's `[aria-expanded]` control) so a keyboard
 * reader isn't dropped at the top of the page.
 *
 * Six menus (account, quick settings, share, add-to-shelf, a shelf book's
 * actions, the book page's Download) each wrote this out by hand, slightly
 * differently — some closed on Escape when shut, none returned focus. For a
 * full overlay that traps focus, use `focusTrap` instead.
 */
export interface DismissableOptions {
	open: boolean;
	onDismiss: () => void;
}

export function dismissable(node: HTMLElement, options: DismissableOptions) {
	let opts = options;

	function onClick(e: MouseEvent) {
		if (opts.open && !node.contains(e.target as Node)) opts.onDismiss();
	}
	function onKeydown(e: KeyboardEvent) {
		if (!opts.open || e.key !== 'Escape') return;
		const hadFocus = node.contains(document.activeElement);
		opts.onDismiss();
		if (hadFocus) node.querySelector<HTMLElement>('[aria-expanded]')?.focus();
	}

	document.addEventListener('click', onClick);
	document.addEventListener('keydown', onKeydown);
	return {
		update(next: DismissableOptions) {
			opts = next;
		},
		destroy() {
			document.removeEventListener('click', onClick);
			document.removeEventListener('keydown', onKeydown);
		}
	};
}
