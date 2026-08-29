import { describe, expect, it } from 'vitest';
import { pointLabel } from './sermonOutline';

describe('sermon outline — pointLabel', () => {
	it('lifts the ALL-CAPS thesis of a homiletic point', () => {
		expect(pointLabel('I. First, we have here A GOSPEL REJECTED. One would…')).toBe(
			'I. A Gospel Rejected'
		);
		expect(pointLabel('II. Let us now take the second head—AN ANSWER PROMISED. We…')).toBe(
			'II. An Answer Promised'
		);
		expect(pointLabel('I. The first head is PRAYER COMMANDED. We are not…')).toBe(
			'I. Prayer Commanded'
		);
	});

	it('keeps the apostrophe in a possessive', () => {
		// `\b` treats an apostrophe as a word boundary, so the old title-caser
		// capitalised the letter after it: `WHERE GOD'S PEOPLE OFTEN ARE` came
		// out as "Where God'S People Often Are" in consolation-in-the-furnace.
		expect(pointLabel("I. We commence by gazing into the place WHERE GOD'S PEOPLE ARE.")).toBe(
			"I. Where God's People Are"
		);
	});

	it('lifts a ONE-word thesis too', () => {
		// The caps RUN needs two words, so these three points across the corpus
		// fell through to the sentence fallback and came out as noise.
		expect(pointLabel('I. First, there is a COMPLAINT. How many a Christian…')).toBe(
			'I. Complaint'
		);
		expect(pointLabel('III. Now for the APPLICATION. A word or two with you…')).toBe(
			'III. Application'
		);
		// Five letters minimum, so an initial or a stray capital is not a thesis.
		expect(pointLabel('II. Then said Mr. A. B. to his friend, and they walked on.')).toBeNull();
	});

	it('uses the opening sentence only when it reads as a title', () => {
		// Short, and names the division — these are real points in
		// salvation-by-faith and the-joy-of-the-lord.
		expect(pointLabel('I. What faith it is through which we are saved. And first…')).toBe(
			'I. What Faith It Is Through Which We Are Saved'
		);
		expect(pointLabel('II. The secret of this joy. Consider now…')).toBe(
			'II. The Secret Of This Joy'
		);
	});

	it('emits nothing rather than a truncated sentence', () => {
		// The promise at the top of the module is precision over recall, and the
		// old unconditional fallback broke it: eleven points across eight sermons
		// became half-sentences in the drawer. Both guards were measured against
		// the corpus — a title is short, and it does not open with a connective.
		expect(
			pointLabel('I. I argue that He will, first, when I remember that He hears the lowly ravens.')
		).toBeNull();
		expect(pointLabel('VI. But I have mightier arguments and nearer the mark.')).toBeNull();
		expect(pointLabel('V. Again, there is yet another and a far mightier argument.')).toBeNull();
		// No sentence end at all is not a title either.
		expect(pointLabel('IV. ' + Array.from({ length: 20 }, (_, i) => `word${i}`).join(' '))).toBeNull();
	});

	it('ignores paragraphs that are not points', () => {
		expect(pointLabel('This is ordinary prose about prayer.')).toBeNull();
		expect(pointLabel('In 1 Corinthians 2:2 Paul writes…')).toBeNull();
		// A lone initial or mid-sentence roman numeral is not a point.
		expect(pointLabel('I am persuaded that nothing can separate us.')).toBeNull();
	});

	it('reads the accented alphabets, not just ASCII', () => {
		// `[A-Z]` cuts at the first accented letter, so the Spanish and
		// Portuguese sermons rendered "III. Aplica", "III. Exhortaci" and
		// "III. O Benef" — a label chopped mid-word.
		expect(pointLabel('III. Ahora para la APLICACIÓN. Una palabra o dos…')).toBe(
			'III. Aplicación'
		);
		expect(pointLabel('III. O BENEFÍCIO QUE ESTES RECEBEM. Ora…')).toBe(
			'III. O Benefício Que Estes Recebem'
		);
		// And the title-caser must raise an accented opening: `[a-z]` left
		// "é Necessário Que A Nossa Causa…" in lower case.
		expect(pointLabel('I. é necessário que a nossa causa seja posta. Ora…')).toBe(
			'I. É Necessário Que A Nossa Causa Seja Posta'
		);
	});

	it('never truncates a label it inferred from a sentence', () => {
		// The guard that holds in EVERY language. `CONNECTIVE` is English-only
		// by nature, so the half-sentences it removes from the-ravens-cry would
		// have survived in its Portuguese and Spanish translations; a sentence
		// that does not fit was not a title, and that rule needs no vocabulary.
		expect(
			pointLabel('V. De novo, há ainda outro e muito mais poderoso argumento a usar. Quando…')
		).toBeNull();
		expect(
			pointLabel('VI. Mas tenho argumentos mais poderosos e mais próximos do alvo. Quando…')
		).toBeNull();
	});

	it('accepts a head that closes with a colon or dash', () => {
		// `the-possibilities-of-faith` opens its first point this way, and lost
		// it while keeping points II and III — in five languages.
		expect(pointLabel('I. Let us consider the possibilities of faith:-- and first…')).toBe(
			'I. Let Us Consider The Possibilities Of Faith'
		);
	});

	it('caps a very long thesis', () => {
		// the-immutability-of-god II runs to nine words; anything longer is
		// trimmed rather than allowed to fill the drawer.
		const label = pointLabel(
			'II. Now secondly, a word on THE PERSONS TO WHOM THIS UNCHANGEABLE GOD IS A GREAT BENEFIT. Now, who…'
		);
		expect(label!.endsWith('…')).toBe(true);
		expect(label!.split(' ').length).toBeLessThanOrEqual(11);
	});
});
