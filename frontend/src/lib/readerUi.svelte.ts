/**
 * Cross-component reader UI state. `focus` (immersive mode) is read by the root
 * layout to hide the global header/footer and by the reader to hide its own top
 * bar, so the whole chrome collapses to just the text. It is intentionally NOT
 * persisted — focus mode is a per-reading-session choice and always resets.
 */
class ReaderUi {
	focus = $state(false);

	toggleFocus() {
		this.focus = !this.focus;
	}
	exitFocus() {
		this.focus = false;
	}
}

export const readerUi = new ReaderUi();
