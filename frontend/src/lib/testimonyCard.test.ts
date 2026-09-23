import { describe, expect, it } from 'vitest';
import { cleanEntry } from './journal';
import { testimonyText, type TestimonyLabels } from './testimonyCard';

const labels: TestimonyLabels = {
	heading: 'Answered prayer',
	prayed: 'We prayed',
	answered: 'God answered',
	forPerson: (p) => `for ${p}`,
	meta: (days, on) => `Prayed for ${days} days · ${on}`
};
const DAY = 86_400_000;
const prayer = cleanEntry({
	id: 'p',
	kind: 'prayer',
	title: "Dad's surgery",
	body: 'Skill for the doctors.',
	person: 'Dad',
	createdAt: Date.UTC(2026, 8, 1, 12),
	answeredAt: Date.UTC(2026, 8, 1, 12) + 13 * DAY,
	answer: 'Home within a week. Thank you, Lord.'
})!;
const opts = { includeRequest: true, includePerson: false, locale: 'en' };

describe('testimony card text', () => {
	it('keeps who it was for off the card unless the reader includes it', () => {
		expect(testimonyText(prayer, opts, labels).request).toBe("We prayed: Dad's surgery");
		expect(testimonyText(prayer, { ...opts, includePerson: true }, labels).request).toBe(
			"We prayed for Dad: Dad's surgery"
		);
	});

	it('can leave the request off, and always carries the answer and how long it was prayed', () => {
		const t = testimonyText(prayer, { ...opts, includeRequest: false }, labels);
		expect(t.request).toBeNull();
		expect(t.answer).toBe('Home within a week. Thank you, Lord.');
		expect(t.meta).toBe('Prayed for 13 days · September 14, 2026');
	});

	it('still testifies when the answer has no words', () => {
		const t = testimonyText({ ...prayer, answer: '' }, opts, labels);
		expect(t.answer).toBe('God answered');
	});
});
