import { readJSON, writeJSON } from './persisted';

/**
 * The highlight counts at which a signed-out reader is told how many they've
 * kept on this device (and that the Notebook, with an account, keeps them).
 *
 * Each milestone shows once per device, ever: the highest one shown is
 * stored, so a reader hovering around 3 isn't told "3" every session, and a
 * count that jumps past one (synced or bulk marks) still gets it.
 */
export const HIGHLIGHT_MILESTONES = [3, 10, 25] as const;
const KEY = 'ochorus:highlight_milestone';

/** The milestone to announce at `count`, given the last one shown, or null. */
export function milestoneFor(count: number, lastShown: number): number | null {
	let hit: number | null = null;
	for (const m of HIGHLIGHT_MILESTONES) if (m > lastShown && count >= m) hit = m;
	return hit;
}

export function lastMilestone(): number {
	const v = readJSON<number>(KEY, 0);
	return typeof v === 'number' ? v : 0;
}

export function recordMilestone(m: number): void {
	writeJSON(KEY, m);
}

/** All milestones shown: nothing left to count for. */
export const milestonesDone = (last: number) =>
	last >= HIGHLIGHT_MILESTONES[HIGHLIGHT_MILESTONES.length - 1];
