import { describe, expect, it } from 'vitest';
import { syncedAhead, SAME_CHAPTER_GAP } from './resumeSync';

const at = (h: number) => h * 3_600_000; // "hours ago" as a clock, larger = later

describe('syncedAhead', () => {
	it('offers a newer server position in a later chapter', () => {
		const server = { order: 7, p: 3, at: at(10) };
		expect(syncedAhead({ order: 3, p: 12, at: at(2) }, server, 3)).toBe(server);
	});

	it('is silent when the server row is not newer than this device (its own past, or a start-over)', () => {
		expect(syncedAhead({ order: 1, p: 0, at: at(10) }, { order: 7, p: 3, at: at(9) }, 1)).toBeNull();
		expect(syncedAhead({ order: 3, p: 0, at: at(5) }, { order: 7, p: 3, at: at(5) }, 3)).toBeNull();
	});

	it('is silent when there is no synced position', () => {
		expect(syncedAhead({ order: 3, p: 0, at: at(1) }, null, 3)).toBeNull();
	});

	it('measures against the chapter being opened, not a stale local record', () => {
		const local = { order: 2, p: 4, at: at(1) };
		// Reader picked chapter 7 by hand; the account is at 7 too — no offer.
		expect(syncedAhead(local, { order: 7, p: 2, at: at(5) }, 7)).toBeNull();
		// …but the account is at 9 — offer.
		expect(syncedAhead(local, { order: 9, p: 0, at: at(5) }, 7)).not.toBeNull();
		// Opened chapter 7, account behind at 5 — never offer going backwards.
		expect(syncedAhead(local, { order: 5, p: 0, at: at(5) }, 7)).toBeNull();
	});

	it('same chapter: offers only a meaningful paragraph gap', () => {
		const local = { order: 4, p: 10, at: at(1) };
		expect(syncedAhead(local, { order: 4, p: 10 + SAME_CHAPTER_GAP - 1, at: at(2) }, 4)).toBeNull();
		expect(syncedAhead(local, { order: 4, p: 10 + SAME_CHAPTER_GAP, at: at(2) }, 4)).not.toBeNull();
	});

	it('a device that never opened the book is offered any later chapter, or a few paragraphs in', () => {
		expect(syncedAhead(null, { order: 2, p: 0, at: at(1) }, 1)).not.toBeNull();
		expect(syncedAhead(null, { order: 1, p: SAME_CHAPTER_GAP, at: at(1) }, 1)).not.toBeNull();
		expect(syncedAhead(null, { order: 1, p: 1, at: at(1) }, 1)).toBeNull();
	});
});
