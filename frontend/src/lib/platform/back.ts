/**
 * What Android's Back closes before it navigates: a stack of close callbacks,
 * one per open overlay (sheet, dialog, menu, popover, the selection bar). An
 * overlay registers when it opens and unregisters when it closes; Back calls
 * the most recently opened one. A callback, not a synthetic Escape: Escape
 * reaches an overlay only if focus happens to be inside it, and Back must
 * never navigate out from under an open dialog (a note being written).
 *
 * Pure (no Capacitor), so it is unit-tested directly; $lib/platform's
 * `onBack` feeds it in the app and is a no-op on the website.
 */
export function createBackStack() {
	const stack: { close: () => void }[] = [];
	return {
		/** Register `close` as the topmost overlay; returns the unregister. */
		push(close: () => void): () => void {
			const entry = { close };
			stack.push(entry);
			return () => {
				const i = stack.indexOf(entry);
				if (i >= 0) stack.splice(i, 1);
			};
		},
		/** Close the topmost overlay. False when nothing is open. The entry is
		 *  dropped either way, so an overlay that fails to close costs one press,
		 *  never a Back button that does nothing. */
		pop(): boolean {
			const top = stack.pop();
			if (!top) return false;
			top.close();
			return true;
		},
		get size() {
			return stack.length;
		}
	};
}

export const backStack = createBackStack();
