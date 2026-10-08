import { describe, expect, it } from 'vitest';
import { guideWeekHeading } from './leaderGuide';
import { guideSlugs } from './library-public';

describe('guideWeekHeading', () => {
	it('joins the week and the chapter title with an em dash', () => {
		expect(guideWeekHeading('Week %n%', 3, 'The Slough of Despond')).toBe(
			'Week 3 — The Slough of Despond'
		);
	});

	it('follows the localized template', () => {
		expect(guideWeekHeading('Semana %n%', 1, 'El hombre')).toBe('Semana 1 — El hombre');
	});

	it('keeps the week alone when the chapter has no title', () => {
		expect(guideWeekHeading('Week %n%', 2, '  ')).toBe('Week 2');
	});
});

describe('guideSlugs', () => {
	const card = (slug: string) => ({ slug }) as never;

	it('lists each guided book once, in hub order', () => {
		expect(
			guideSlugs([
				{ guides: [card('pilgrims-progress-children'), card('north-wind')] },
				{ guides: [card('pilgrims-progress-teens'), card('north-wind')] }
			])
		).toEqual(['pilgrims-progress-children', 'north-wind', 'pilgrims-progress-teens']);
	});

	it('tolerates an API that sends no guides', () => {
		expect(guideSlugs([{}, { guides: [] }])).toEqual([]);
	});
});
