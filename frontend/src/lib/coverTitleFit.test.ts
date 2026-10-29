import { describe, expect, it } from 'vitest';
import { coverTypeMarkup, titleFit } from './coverCardMarkup';

describe('titleFit', () => {
	it('steps a title up by how short it is', () => {
		expect(titleFit('Holiness')).toBe('fit-short');
		expect(titleFit('Interior Castle')).toBe('fit-mid');
		expect(titleFit('The Pursuit of God')).toBe('fit-roomy');
		expect(titleFit('The Saints’ Everlasting Rest')).toBeNull();
	});

	it('is emitted on the share card, beside long-title', () => {
		const card = (title: string) =>
			coverTypeMarkup({ author: 'A', title, subtitle: '', style: 'revival', lang: 'en', art: true }, '');
		expect(card('Holiness')).toContain('fit-short');
		expect(card('x'.repeat(60))).not.toMatch(/fit-(short|mid|roomy)/);
	});
});
