import { beforeEach, describe, expect, it, vi } from 'vitest';
import { signupNudge, NUDGE_MS } from './signupNudge.svelte';

const nudge = {
	id: 'save',
	textKey: 'nudge.savedToShelf',
	linkKey: 'nudge.openShelf',
	href: '/login',
	source: 'save_toast' as const
};

beforeEach(() => {
	vi.useFakeTimers();
	signupNudge._reset();
});

describe('signupNudge', () => {
	it('shows a nudge, then lets it go after a while', () => {
		expect(signupNudge.offer(nudge)).toBe(true);
		expect(signupNudge.current?.id).toBe('save');
		vi.advanceTimersByTime(NUDGE_MS);
		expect(signupNudge.current).toBeNull();
	});

	it('shows each kind only once a session', () => {
		signupNudge.offer(nudge);
		signupNudge.dismiss();
		expect(signupNudge.offer(nudge)).toBe(false);
		expect(signupNudge.current).toBeNull();
		expect(signupNudge.offer({ ...nudge, id: 'highlight-3' })).toBe(true);
	});
});
