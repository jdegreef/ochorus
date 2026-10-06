import { describe, expect, it, vi } from 'vitest';

const listAudienceLanguages = vi.hoisted(() => vi.fn());
vi.mock('$lib/library-public', () => ({ listAudienceLanguages, getAudienceShelf: vi.fn() }));

const { hubLanguages } = await import('./audienceHubData');

describe('hubLanguages', () => {
	it('gives every hub a list, even one the API does not name', async () => {
		listAudienceLanguages.mockResolvedValueOnce({ young_readers: ['en', 'sw'] });
		expect(await hubLanguages()).toEqual({ young_readers: ['en', 'sw'], teens: [] });
	});

	it('answers "none anywhere" when the call fails — its readers are decoration', async () => {
		listAudienceLanguages.mockRejectedValueOnce(new Error('503'));
		expect(await hubLanguages()).toEqual({ young_readers: [], teens: [] });
	});
});
