/**
 * The Open Word Bible — the translation the library's Bible is printed in.
 *
 * Like Ochorus Originals (`$lib/originals`) it is a byline, not a person
 * (`Author.is_imprint`): the Bible's 66 books are "by" it, but it has no life
 * to tell, so its name links to a page about the translation, /open-word-bible,
 * rather than to an author page with a monogram (`authorPath`). The books
 * themselves live on the Bible hub, /bible ($lib/bible).
 */
import type { BibleText } from './bibleLocales';

export const OWB_SLUG = 'open-word-bible';
export const OWB_PATH = '/open-word-bible';
/** The translation's own home: every sentence's reasoning, every level. */
export const OWB_URL = 'https://openwordbible.org';
export const OWB_READ_URL = 'https://openwordbible.org/read/';

/** The three levels OWB translates every sentence at; Ochorus prints Balanced.
 *  Named and described in each hub locale, for the /open-word-bible page. */
export const OWB_LEVELS: readonly { code: 'OWB-L' | 'OWB-B' | 'OWB-R'; name: BibleText; aim: BibleText }[] = [
	{
		code: 'OWB-L',
		name: { en: 'Literal', es: 'Literal' },
		aim: {
			en: 'Follows the Hebrew and Greek closely, with any word it supplies in brackets: for study beside the original.',
			es: 'Sigue de cerca el hebreo y el griego, con entre corchetes toda palabra que añade: para estudiar junto al original.'
		}
	},
	{
		code: 'OWB-B',
		name: { en: 'Balanced', es: 'Equilibrado' },
		aim: {
			en: 'Accurate and natural: faithful to the original, and easy to read. This is the text you read on Ochorus.',
			es: 'Exacto y natural: fiel al original y fácil de leer. Es el texto que lees en Ochorus.'
		}
	},
	{
		code: 'OWB-R',
		name: { en: 'Readable', es: 'Sencillo' },
		aim: {
			en: 'Plain modern language, made explicit where it helps: for a first reading, or a young reader.',
			es: 'Lenguaje moderno y sencillo, explícito donde ayuda: para una primera lectura o un lector joven.'
		}
	}
];

/** The languages OWB is translating into, English first (its README's list),
 *  named in each hub locale. */
export const OWB_LANGUAGES: readonly BibleText[] = [
	{ en: 'English', es: 'Inglés' },
	{ en: 'Spanish', es: 'Español' },
	{ en: 'French', es: 'Francés' },
	{ en: 'Swahili', es: 'Suajili' },
	{ en: 'Vietnamese', es: 'Vietnamita' },
	{ en: 'Korean', es: 'Coreano' },
	{ en: 'Portuguese', es: 'Portugués' },
	{ en: 'Amharic', es: 'Amárico' },
	{ en: 'Hindi', es: 'Hindi' },
	{ en: 'Russian', es: 'Ruso' },
	{ en: 'Ukrainian', es: 'Ucraniano' },
	{ en: 'Japanese', es: 'Japonés' }
];

/** The three covers fanned beside the page's heading (the fan shows three):
 *  the Law, the Psalms and a Gospel, Hebrew and Greek names side by side. */
export const OWB_FAN = ['genesis', 'psalms', 'gospel-of-john'] as const;
