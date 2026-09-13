import { describe, it, expect } from 'vitest';
import { advanceSession, SESSION_GAP_MS, type Session } from './sessionClock';

const ctx = { kind: 'book' as const, slug: 'humility', language: 'en' };
const ctx2 = { kind: 'sermon' as const, slug: 'all-of-grace', language: 'en' };

// Deterministic ids so we can assert rollovers.
function ids() {
	let n = 0;
	return () => `id${++n}`;
}

describe('advanceSession', () => {
	it('starts a sitting from nothing', () => {
		const now = 1_000_000;
		const { session, rolled } = advanceSession(null, 40_000, now, ctx, ids());
		expect(rolled).toBe(true);
		expect(session.clientId).toBe('id1');
		expect(session.seconds).toBe(40);
		expect(session.startedAt).toBe(now - 40_000);
		expect(session.lastAt).toBe(now);
		expect(session.slug).toBe('humility');
	});

	it('accumulates within the gap and keeps the sitting', () => {
		const newId = ids();
		const now = 1_000_000;
		const a = advanceSession(null, 30_000, now, ctx, newId).session;
		const b = advanceSession(a, 20_000, now + 60_000, ctx, newId);
		expect(b.rolled).toBe(false);
		expect(b.session.clientId).toBe('id1'); // same sitting
		expect(b.session.seconds).toBe(50); // 30 + 20
		expect(b.session.startedAt).toBe(a.startedAt); // unchanged
		expect(b.session.lastAt).toBe(now + 60_000);
	});

	it('rolls a new sitting after a long gap', () => {
		const newId = ids();
		const now = 1_000_000;
		const a = advanceSession(null, 30_000, now, ctx, newId).session;
		const b = advanceSession(a, 25_000, now + SESSION_GAP_MS + 1, ctx2, newId);
		expect(b.rolled).toBe(true);
		expect(b.session.clientId).toBe('id2'); // fresh sitting
		expect(b.session.seconds).toBe(25); // reset, not 55
		expect(b.session.kind).toBe('sermon'); // new context
	});

	it('keeps the original sitting context on continuation', () => {
		const newId = ids();
		const now = 1_000_000;
		const a = advanceSession(null, 10_000, now, ctx, newId).session;
		// A later chunk while reading a different work in the same sitting.
		const b = advanceSession(a, 10_000, now + 5000, ctx2, newId).session;
		expect(b.kind).toBe('book'); // context is the sitting's, set once
		expect(b.slug).toBe('humility');
	});

	it('ignores non-positive time defensively', () => {
		const now = 1_000_000;
		const prev: Session = {
			clientId: 'x',
			startedAt: now - 1000,
			lastAt: now,
			seconds: 5,
			...ctx
		};
		const { session } = advanceSession(prev, 0, now + 1000, ctx, ids());
		expect(session.seconds).toBe(5); // unchanged
		expect(session.lastAt).toBe(now + 1000);
	});
});
