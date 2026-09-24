/**
 * Close-on-click-away / close-on-Escape for a dropdown menu.
 *
 * Apply to the element that wraps BOTH the trigger and its menu:
 *
 *   <div use:dismissable={{ open, onDismiss: () => (open = false) }}>
 *
 * While `open`, a click outside that element or an Escape press calls
 * `onDismiss`. When Escape closes a menu that had focus inside it, focus goes
 * back to the trigger — the wrapper's first `[aria-expanded]` control, which
 * precedes the menu in document order — so a keyboard reader isn't dropped at
 * the top of the page.
 *
 * The document listeners are attached only while the menu is open, so a page
 * of closed menus (a shelf of books, each with its own) costs nothing. For a
 * full overlay that traps focus, use `focusTrap` instead.
 */
export interface DismissableOptions {
	open: boolean;
	onDismiss: () => void;
}

export function dismissable(node: HTMLElement, options: DismissableOptions) {
	// The event's path, not `node.contains(target)`: a menu item that swaps
	// itself out when clicked ("Saved offline" → "Download for offline") is
	// already detached by the time the click bubbles here, so `contains` would
	// call it an outside click and shut the menu under the reader's cursor.
	function onClick(e: MouseEvent) {
		if (!e.composedPath().includes(node)) options.onDismiss();
	}
	function onKeydown(e: KeyboardEvent) {
		if (e.key !== 'Escape') return;
		const hadFocus = node.contains(document.activeElement);
		options.onDismiss();
		if (hadFocus) node.querySelector<HTMLElement>('[aria-expanded]')?.focus();
	}

	let listening = false;
	function listen(on: boolean) {
		if (on === listening) return;
		listening = on;
		if (on) {
			document.addEventListener('click', onClick);
			document.addEventListener('keydown', onKeydown);
		} else {
			document.removeEventListener('click', onClick);
			document.removeEventListener('keydown', onKeydown);
		}
	}

	listen(options.open);
	return {
		update(next: DismissableOptions) {
			options = next;
			listen(next.open);
		},
		destroy() {
			listen(false);
		}
	};
}
