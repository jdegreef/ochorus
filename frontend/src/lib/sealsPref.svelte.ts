import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';

/**
 * Whether reading seals show at all — a device preference, on by default, for
 * readers who would rather not have them. Off hides them everywhere they
 * appear (the Bookshelf section, the end of a book); nothing is lost, since a
 * seal is worked out from reading, not stored.
 */
export const SEALS_PREF_KEY = 'ochorus:seals';

class SealsPref {
	on = $state(browser ? readJSON<boolean>(SEALS_PREF_KEY, true) : true);

	set(on: boolean) {
		this.on = on;
		writeJSON(SEALS_PREF_KEY, on);
	}
}

export const sealsPref = new SealsPref();
