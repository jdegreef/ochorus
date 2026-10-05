import { describe, expect, it } from 'vitest';
import { welcomeSteps } from './welcomeSteps';

const none = { signedIn: false, read: false, saved: false, marked: false };

describe('welcomeSteps', () => {
	it('lists the four steps in order, none done for a stranger', () => {
		const { steps, done } = welcomeSteps(none);
		expect(steps.map((s) => s.key)).toEqual(['account', 'read', 'save', 'mark']);
		expect(done).toBe(0);
	});

	it('ticks each step from the matching activity', () => {
		const { steps, done } = welcomeSteps({ ...none, signedIn: true, saved: true });
		expect(steps.filter((s) => s.done).map((s) => s.key)).toEqual(['account', 'save']);
		expect(done).toBe(2);
	});

	it('is complete once everything has been tried', () => {
		expect(welcomeSteps({ signedIn: true, read: true, saved: true, marked: true }).done).toBe(4);
	});
});
