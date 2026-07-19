/**
 * Tracks whether writing to localStorage has failed this session (quota
 * exceeded, or storage disabled in private-browsing mode).
 *
 * The reader keeps working from in-memory state after a failed write, but the
 * data — a highlight, a note, a bookmark, the reading place — won't survive a
 * reload. That silent loss is worse than a warning, so `writeJSON` flips this
 * flag on failure and a toast tells the reader their notes may not be saved.
 */
class StorageHealth {
	/** True once any persistence write has failed this session. */
	writeFailed = $state(false);

	fail() {
		this.writeFailed = true;
	}

	/** Dismiss the warning. It reappears if another write later fails. */
	acknowledge() {
		this.writeFailed = false;
	}
}

export const storageHealth = new StorageHealth();
