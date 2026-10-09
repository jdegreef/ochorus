import { beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * Prompt views and starts are counted by the API too (Admin → Users → Prompt
 * funnel), alongside Plausible.
 */
const apiFetch = vi.hoisted(() => vi.fn((_url: string, _init?: RequestInit) => Promise.resolve()));
vi.mock('./api', () => ({ apiFetch }));

const { _resetSeen, noteSignupSource, promptSeen, signupStarted } = await import('./signupSource');

const posted = () =>
	apiFetch.mock.calls.map(([url, init]) => [url, JSON.parse(init?.body as string)]);

beforeEach(() => {
	localStorage.clear();
	apiFetch.mockClear();
	_resetSeen();
});

describe('prompt counts', () => {
	it('counts a prompt seen once per page session', () => {
		promptSeen('chapter_end');
		promptSeen('chapter_end');
		promptSeen('footer');
		expect(posted()).toEqual([
			['/api/auth/prompt-event/', { source: 'chapter_end', kind: 'seen' }],
			['/api/auth/prompt-event/', { source: 'footer', kind: 'seen' }]
		]);
	});

	it('counts a start against the prompt the reader followed', () => {
		noteSignupSource('plan_day');
		signupStarted();
		expect(posted()).toEqual([['/api/auth/prompt-event/', { source: 'plan_day', kind: 'started' }]]);
		// Google's sign-in leaves the page at once; the count must outlive it.
		expect(apiFetch.mock.calls[0][1]?.keepalive).toBe(true);
	});

	it('counts nothing for a start that followed no prompt', () => {
		signupStarted();
		expect(apiFetch).not.toHaveBeenCalled();
	});

	it('never lets a failed count reach the prompt', async () => {
		apiFetch.mockImplementationOnce(() => Promise.reject(new Error('offline')));
		expect(() => promptSeen('header')).not.toThrow();
		await Promise.resolve();
	});
});
