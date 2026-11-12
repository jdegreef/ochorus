import { describe, expect, it } from 'vitest';
import { adventOffer, chooseFooterPitch, footerPage, FOOTER_SOURCE, SEASON_LEAD_DAYS } from './footerSignup';
import { SIGNUP_SOURCES } from './signupSource';

describe('footer sign-up: which message', () => {
	const none = { hasProgressBook: false, page: null, inSeason: false };
	const page = { kind: 'book' as const, title: 'Humility' };

	it('names a book in progress before anything else', () => {
		expect(chooseFooterPitch({ hasProgressBook: true, page, inSeason: true })).toBe('progress');
	});

	it('then the page, then the season, then the band', () => {
		expect(chooseFooterPitch({ ...none, page, inSeason: true })).toBe('page');
		expect(chooseFooterPitch({ ...none, inSeason: true })).toBe('season');
		expect(chooseFooterPitch(none)).toBe('band');
	});

	it('gives every message a sign-up source the backend knows', () => {
		for (const source of Object.values(FOOTER_SOURCE)) expect(SIGNUP_SOURCES).toContain(source);
		expect(new Set(Object.values(FOOTER_SOURCE)).size).toBe(4);
	});
});

describe('footer sign-up: the page it sits under', () => {
	it('names the four kinds of work from their route data', () => {
		expect(footerPage('/books/[slug]', { book: { title: 'Humility' } })).toEqual({ kind: 'book', title: 'Humility' });
		expect(footerPage('/sermons/[slug]', { sermon: { title: 'Thought and Action' } })).toEqual({
			kind: 'sermon',
			title: 'Thought and Action'
		});
		expect(footerPage('/authors/[slug]', { author: { name: 'Andrew Murray' } })).toEqual({
			kind: 'author',
			name: 'Andrew Murray'
		});
		expect(footerPage('/plans/[slug]', { plan: { title: 'Humility in 12 Days' } })).toEqual({
			kind: 'plan',
			title: 'Humility in 12 Days'
		});
	});

	it('is null anywhere else, or without the data', () => {
		expect(footerPage('/topics', {})).toBeNull();
		expect(footerPage(null, {})).toBeNull();
		expect(footerPage('/books/[slug]', {})).toBeNull();
		expect(footerPage('/books/[slug]', { book: { title: 42 } })).toBeNull();
	});
});

describe('footer sign-up: Advent', () => {
	// Advent Sunday 2026 is 29 November.
	it('counts down through the lead-up and runs to Christmas Eve', () => {
		expect(adventOffer(new Date(2026, 10, 12))?.daysToGo).toBe(17);
		expect(adventOffer(new Date(2026, 10, 29))?.daysToGo).toBe(0);
		expect(adventOffer(new Date(2026, 11, 24))?.daysToGo).toBe(0);
	});

	it('is quiet outside the season and its lead-up', () => {
		expect(adventOffer(new Date(2026, 11, 25))).toBeNull();
		expect(adventOffer(new Date(2026, 6, 1))).toBeNull();
		const before = new Date(2026, 10, 29 - SEASON_LEAD_DAYS - 1);
		expect(adventOffer(before)).toBeNull();
	});
});
