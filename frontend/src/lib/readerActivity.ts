import { allProgress } from './progress';
import { favorites } from './favorites.svelte';
import { marks } from './marks.svelte';
import { planProgress } from './planProgress.svelte';

/**
 * What this reader has done on this device, as three yes/no answers — the one
 * place "is this a new reader?" is decided. OnboardingCard shows while none of
 * the first two is true; the /welcome checklist ticks its steps from all three;
 * HomeDashboard skips the welcome redirect for a reader who has started.
 * Browser only: the stores are localStorage.
 */
export interface ReaderActivity {
	/** Any book, sermon or plan progress. */
	read: boolean;
	/** Anything on the bookshelf. */
	saved: boolean;
	/** Any highlight or note. */
	marked: boolean;
}

export function readerActivity(language: string): ReaderActivity {
	return {
		read: allProgress().length > 0 || planProgress.started().length > 0,
		saved: favorites.count() > 0,
		marked: marks.allByEdition(language).some((w) => w.marks.length > 0)
	};
}

/** A reader who has read or saved anything is no longer new. */
export const hasStarted = (a: ReaderActivity): boolean => a.read || a.saved;
