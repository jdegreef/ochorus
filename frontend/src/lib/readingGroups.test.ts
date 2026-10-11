import { afterEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({ apiFetch: vi.fn(async () => ({})) }));
vi.mock('./api', () => api);

const { createGroup, getGroup, joinGroup, leaveGroup } = await import('./readingGroups');

afterEach(() => api.apiFetch.mockClear());

describe('reading groups API', () => {
	it('creates a group from the dates the link carries', async () => {
		await createGroup('school-of-prayer', { start: '2026-10-12', rule: 'weekdays' });
		const [path, init] = api.apiFetch.mock.calls[0] as unknown as [string, RequestInit];
		expect(path).toBe('/api/reading/groups/');
		expect(init.method).toBe('POST');
		expect(JSON.parse(init.body as string)).toEqual({
			plan_slug: 'school-of-prayer',
			start_on: '2026-10-12',
			reading_days: 'weekdays'
		});
	});

	it('asks for a day’s count only when there is a day', async () => {
		await getGroup('abc_DEF-123', 4);
		await getGroup('abc_DEF-123', null);
		expect(api.apiFetch.mock.calls.map((c) => (c as unknown[])[0])).toEqual([
			'/api/reading/groups/abc_DEF-123/?day=4',
			'/api/reading/groups/abc_DEF-123/'
		]);
	});

	it('joins and leaves by membership', async () => {
		await joinGroup('abc_DEF-123');
		await leaveGroup('abc_DEF-123');
		expect(api.apiFetch.mock.calls.map((c) => [(c as unknown[])[0], ((c as unknown[])[1] as RequestInit).method])).toEqual([
			['/api/reading/groups/abc_DEF-123/membership/', 'PUT'],
			['/api/reading/groups/abc_DEF-123/membership/', 'DELETE']
		]);
	});
});
