/**
 * Whether the command palette is open.
 *
 * The flag lived inside CommandPalette, which meant the ONLY way to open the
 * palette was the ⌘K handler the component registered on the window — so on a
 * phone or tablet, where there is no keyboard, it could not be opened at all,
 * and nothing in the chrome hinted it existed. Lifting the flag lets the nav
 * carry a visible trigger for the same surface.
 *
 * Deliberately not persisted: an overlay that reopened itself on the next visit
 * would be a bug, not a convenience.
 */
class PaletteUi {
	open = $state(false);

	/** Requests come from the ⌘K shortcut and from the nav's search button. */
	openPalette() {
		this.open = true;
	}
	close() {
		this.open = false;
	}
	toggle() {
		this.open = !this.open;
	}
}

export const paletteUi = new PaletteUi();
