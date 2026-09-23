import { browser } from '$app/environment';
import { readJSON, writeJSON } from './persisted';
import type { PrayerGroup } from './journal';

/**
 * The reminders the reader added for whole prayer lists — "Family every
 * morning", "Missions on Sundays". The reminder itself is a repeating event in
 * the reader's own calendar (which reaches every device they use); this only
 * records which one was added, so the list can say so. A per-device record,
 * like the reading reminder in Settings.
 */
export const GROUP_REMIND_KEY = 'ochorus:group-reminders';

type Store = Partial<Record<PrayerGroup | 'other', string>>;

class GroupReminders {
	all = $state<Store>({});

	constructor() {
		if (browser) this.all = readJSON<Store>(GROUP_REMIND_KEY, {});
	}

	get(group: PrayerGroup | ''): string {
		return this.all[group || 'other'] ?? '';
	}

	set(group: PrayerGroup | '', remind: string) {
		const next = { ...this.all };
		if (remind) next[group || 'other'] = remind;
		else delete next[group || 'other'];
		this.all = next;
		writeJSON(GROUP_REMIND_KEY, next);
	}
}

export const groupReminders = new GroupReminders();
