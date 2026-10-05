import { describe, expect, it } from 'vitest';
import { inboxFor } from './inbox';

describe('inboxFor', () => {
	it('finds the big webmail providers', () => {
		expect(inboxFor('grace@gmail.com')?.name).toBe('Gmail');
		expect(inboxFor('  Grace@Hotmail.com ')?.name).toBe('Outlook');
		expect(inboxFor('a@icloud.com')?.url).toBe('https://www.icloud.com/mail');
	});

	it('offers nothing for other or malformed addresses', () => {
		expect(inboxFor('pastor@stmarks.org')).toBeNull();
		expect(inboxFor('not-an-email')).toBeNull();
		expect(inboxFor('a@gmail.com.evil.test')).toBeNull();
	});
});
