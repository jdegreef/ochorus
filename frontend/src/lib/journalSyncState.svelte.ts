import { browser } from '$app/environment';
import { readJSON } from './persisted';
import { JOURNAL_DIRTY_KEY } from './reading-schema';
import { JOURNAL_PENDING_EVENT } from './readingSync';

/**
 * Where the Notebook's writing stands — reactive, for the sync indicator:
 * which entries are only on this device (owed to the account, per the pending
 * map readingSync keeps) and whether the browser is online. Whether the reader
 * is signed in comes from `auth`; together they say "saved on this device",
 * "waiting to sync", "offline" or "synced".
 */
class JournalSyncState {
	pending = $state<Record<string, number>>({});
	online = $state(true);

	constructor() {
		if (!browser) return;
		this.online = navigator.onLine;
		this.#read();
		const read = () => this.#read();
		window.addEventListener(JOURNAL_PENDING_EVENT, read);
		// Another tab's write, a sign-in merge, a sign-out wipe.
		window.addEventListener('ochorus:sync', read);
		window.addEventListener('online', () => (this.online = true));
		window.addEventListener('offline', () => (this.online = false));
	}

	#read() {
		this.pending = readJSON<Record<string, number>>(JOURNAL_DIRTY_KEY, {});
	}

	/** Entries the account doesn't have yet. */
	get count(): number {
		return Object.keys(this.pending).length;
	}

	/** Whether this entry is only on this device so far. */
	isPending(id: string): boolean {
		return id in this.pending;
	}
}

export const journalSync = new JournalSyncState();
